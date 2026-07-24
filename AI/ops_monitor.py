"""
Ops 모니터링 에이전트 - Langfuse 트레이스를 조회·집계해 이상 패턴 후보를 뽑는다.

scripts/debug_langfuse_api.py로 확인된 실제 응답 구조(trace.output에
LangGraph 최종 상태 전체가 그대로 들어있음 - cls, rule, rewrite_count,
regenerate_count, answer_confidence, route 등)를 그대로 활용한다.

집계만 하고 "결론"은 내리지 않는다 - 숫자 근거와 LLM의 해석을 분리해서
보여주는 것이 원칙(analyze_score_distribution.py 등에서 지켜온 방식과 동일).
"""
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Any

from BE.core.config import settings
from AI.llm import call_llm, LLMError
from AI.prompts import OPS_MONITOR_SYSTEM

# "노이즈 vs 패턴"을 가르는 최소 건수/비율 - 이건 "해석"이 아니라 "계산"이므로
# 프롬프트 문장이 아니라 코드가 결정론적으로 판정한다(LLM에게 매번 안정적으로
# 지켜질 거라 기대하지 않음 - 이번 세션 내내 겪은 것처럼 숫자 규칙을 프롬프트
# 문장으로만 강제하면 흔들릴 수 있음).
_MIN_RETRY_COUNT_FOR_PATTERN = 3     # 한 카테고리 안에서 이 이상이어야 "국한된 문제"로 판정
_WIDESPREAD_MIN_CATEGORY_SHARE = 0.6  # 전체 카테고리 중 이 비율 이상에서 재시도가 있어야 "광범위"
_WIDESPREAD_MIN_RETRY_RATE = 0.3      # 동시에 전체 재시도율도 이 이상이어야 "광범위"

_TRACES_URL_TMPL = "{host}/api/public/traces"


def fetch_recent_traces(hours: int = 24, max_traces: int = 500) -> list[dict]:
    """최근 N시간 이내의 트레이스를 전부 가져온다(페이지네이션 처리 포함).
    max_traces에 도달하면 중단 - 하루치 로그가 예상보다 훨씬 많을 경우의
    안전장치(무한정 API 호출을 막기 위함)."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    url = _TRACES_URL_TMPL.format(host=settings.langfuse_host.rstrip("/"))
    auth = (settings.langfuse_public_key, settings.langfuse_secret_key)

    traces: list[dict] = []
    page = 1
    while len(traces) < max_traces:
        resp = requests.get(
            url,
            params={"limit": 100, "page": page, "fromTimestamp": since.isoformat()},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("data", [])
        traces.extend(batch)

        meta = data.get("meta", {})
        total_pages = meta.get("totalPages", page)
        if page >= total_pages or not batch:
            break
        page += 1

    return traces[:max_traces]


def _get_output_field(trace: dict, *keys: str, default: Any = None) -> Any:
    """trace["output"]["a"]["b"] 처럼 중첩된 값을 안전하게 꺼낸다.
    output이 비어있거나(처리 중 실패한 트레이스 등) 중간 키가 없어도 죄측
    default로 안전하게 처리 - 집계 도중 하나의 이상한 트레이스 때문에 전체가
    죽는 것을 방지."""
    node = trace.get("output") or {}
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k)
        if node is None:
            return default
    return node


def _classify_pattern(category_retry_count: dict, category_totals: dict, retry_rate: float) -> dict:
    """
    "국한된 문제 / 광범위한 문제 / 특이사항 없음"을 코드가 결정론적으로 판정한다.
    이건 수치 규칙(임계값 비교)이라 "계산"의 영역이고, LLM에게 맡길 "해석"의
    영역이 아니다 - LLM은 이 판정 결과를 왜 그런지 자연스럽게 설명하는 역할만
    한다(build_report_prompt/OPS_MONITOR_SYSTEM 참고).
    """
    concentrated = [cat for cat, cnt in category_retry_count.items() if cnt >= _MIN_RETRY_COUNT_FOR_PATTERN]
    categories_with_any_retry = [cat for cat, cnt in category_retry_count.items() if cnt > 0]
    n_categories = len(category_totals) or 1

    widespread = (
        len(categories_with_any_retry) / n_categories >= _WIDESPREAD_MIN_CATEGORY_SHARE
        and retry_rate >= _WIDESPREAD_MIN_RETRY_RATE
    )

    if widespread:
        label = "⚠️ 광범위한 문제"
        verdict = "광범위한 문제 - 대부분의 카테고리에서 비슷하게 재시도가 발생함"
    elif concentrated:
        cats_str = "·".join(concentrated)
        label = f"⚠️ {cats_str} 국한 문제"
        verdict = f"특정 카테고리 국한 문제 - {cats_str}에서만 재시도가 몰림(각 {_MIN_RETRY_COUNT_FOR_PATTERN}건 이상)"
    else:
        label = "✅ 특이사항 없음"
        verdict = "특이사항 없음 - 재시도가 있더라도 카테고리당 건수가 적어(각 2건 이하) 패턴으로 보기엔 근거 부족"

    return {"verdict": verdict, "label": label, "widespread": widespread, "concentrated_categories": concentrated}


def aggregate_stats(traces: list[dict]) -> dict:
    """트레이스 목록을 집계한다. 이상 패턴 '후보'만 뽑고, 그게 진짜 문제인지
    판단은 이 함수가 아니라 이후 LLM 해석 단계·사람이 한다."""
    n = len(traces)
    if n == 0:
        return {"total": 0}

    routes = Counter()
    domains = Counter()
    categories = Counter()
    confidences = Counter()
    retry_count = 0
    hallucination_fail = 0
    answer_fail = 0
    category_totals = Counter()
    category_retries = Counter()
    flagged = []  # (질문, 사유) - 리포트에 예시로 넣을 것

    for t in traces:
        route = _get_output_field(t, "route", default="(알수없음)")
        routes[route] += 1

        domain = _get_output_field(t, "cls", "domain", default="(알수없음)")
        domains[domain] += 1
        category = _get_output_field(t, "cls", "category", default="(알수없음)")
        categories[category] += 1

        confidence = _get_output_field(t, "answer_confidence", default="(알수없음)")
        confidences[confidence] += 1

        rewrite = _get_output_field(t, "rewrite_count", default=0) or 0
        regenerate = _get_output_field(t, "regenerate_count", default=0) or 0
        had_retry = (rewrite > 0) or (regenerate > 0)
        if had_retry:
            retry_count += 1

        category_totals[category] += 1
        if had_retry:
            category_retries[category] += 1

        hallucination_ok = _get_output_field(t, "hallucination_ok", default=True)
        answer_ok = _get_output_field(t, "answer_ok", default=True)
        if hallucination_ok is False:
            hallucination_fail += 1
        if answer_ok is False:
            answer_fail += 1

        # 재시도가 있었거나 확신도가 낮은 경우만 리포트 예시 후보로 남김
        if had_retry or confidence == "insufficient":
            question = _get_output_field(t, "text", default="") or t.get("input", {}).get("text", "")
            reason_parts = []
            if rewrite > 0:
                reason_parts.append(f"재검색 {rewrite}회")
            if regenerate > 0:
                reason_parts.append(f"재생성 {regenerate}회")
            if confidence == "insufficient":
                reason_parts.append("확신도 insufficient")
            flagged.append({"question": question[:80], "reason": ", ".join(reason_parts), "category": category})

    pattern = _classify_pattern(dict(category_retries), dict(category_totals), retry_count / n)

    return {
        "total": n,
        "route_dist": dict(routes),
        "domain_dist": dict(domains),
        "category_dist": dict(categories),
        "confidence_dist": dict(confidences),
        "retry_rate": retry_count / n,
        "category_retry_count": dict(category_retries),  # 카테고리별 재시도 "건수"(원본)
        "category_retry_rate": {
            cat: round(category_retries[cat] / category_totals[cat], 3)
            for cat in category_totals
        },
        "pattern_verdict": pattern["verdict"],  # 코드가 이미 결정론적으로 내린 판정(긴 설명, LLM 프롬프트용)
        "pattern_label": pattern["label"],      # 짧은 라벨(이메일 제목 등에 그대로 쓰기 좋음)
        "hallucination_fail_rate": hallucination_fail / n,
        "answer_fail_rate": answer_fail / n,
        "flagged_examples": flagged[:15],  # 리포트가 너무 길어지지 않게 상한
        "flagged_count": len(flagged),
    }


def build_report_prompt(stats: dict) -> str:
    """LLM에게 넘길 user 프롬프트. 숫자는 그대로 보여주고, '해석'만 LLM에게
    맡긴다 - 숫자를 LLM이 다시 계산하게 하지 않는다(계산 오류 방지)."""
    if stats["total"] == 0:
        return "[집계 대상] 최근 기간 동안 처리된 문의가 없습니다."

    category_retry_str = ", ".join(
        f"{cat}: {stats['category_retry_count'].get(cat, 0)}/{stats['category_dist'][cat]}건"
        f"({stats['category_retry_rate'][cat]:.0%})"
        for cat in stats["category_dist"]
    )
    lines = [
        f"[사전 판정 — 이미 코드로 확정됨. 이 판정을 그대로 받아들이고 왜 이런 "
        f"판정이 나왔는지 아래 숫자로 설명만 하라. 이 판정 자체를 다시 계산하거나 "
        f"의심하거나 다른 결론으로 바꾸지 마라] {stats['pattern_verdict']}",
        f"[집계 기간] 최근 문의 {stats['total']}건",
        f"[도메인 분포] {stats['domain_dist']}",
        f"[카테고리별 문항 수] {stats['category_dist']}",
        f"[카테고리별 재시도 발생(재시도건수/전체건수, 비율)] {category_retry_str}",
        f"[확신도 분포] {stats['confidence_dist']}",
        f"[전체 재시도(재검색 또는 재생성) 발생률] {stats['retry_rate']:.1%}",
        f"[근거불일치(hallucination) 발생률] {stats['hallucination_fail_rate']:.1%}",
        f"[질문부적합(answer) 발생률] {stats['answer_fail_rate']:.1%}",
        f"[재시도 또는 낮은 확신도로 표시된 문항 수] {stats['flagged_count']}건",
    ]
    if stats["flagged_examples"]:
        lines.append("\n[표시된 문항 예시(최대 15건)]")
        for ex in stats["flagged_examples"]:
            lines.append(f"  - ({ex['category']}) {ex['question']} -> {ex['reason']}")

    return "\n".join(lines)


def generate_ops_report(stats: dict) -> str:
    """집계 결과를 LLM에게 넘겨 해석이 붙은 리포트를 만든다. 숫자 자체는
    build_report_prompt()가 이미 정확히 계산해서 넘기므로, LLM은 그 숫자를
    다시 계산하지 않고 해석만 담당한다(OPS_MONITOR_SYSTEM 지시 참고)."""
    prompt = build_report_prompt(stats)
    try:
        report = call_llm(settings.classifier_model, OPS_MONITOR_SYSTEM, prompt, max_tokens=800)
    except LLMError as e:
        return f"[리포트 생성 실패: {e}]\n\n집계 데이터는 다음과 같습니다:\n{prompt}"
    return report or "[리포트 생성 실패: 빈 응답]"


def send_email_report(subject: str, body: str) -> bool:
    """
    SMTP로 리포트를 발송한다. 발송 설정(smtp_host 등)이 비어있으면 조용히
    False를 반환하고 발송을 건너뛴다 - 이메일 설정 미비가 리포트 생성 자체를
    실패시키면 안 되므로(run_ops_monitor.py가 이 경우 콘솔 출력으로 대체함).
    """
    if not settings.smtp_host or not settings.ops_report_recipient:
        return False

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = settings.ops_report_recipient

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
    return True