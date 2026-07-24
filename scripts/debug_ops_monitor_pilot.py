"""
Ops 모니터링 에이전트 파일럿 검증.

이번 세션에서 실제로 겪은 3종의 상황을 가상 트레이스로 재구성해서, 이
에이전트가 "우리가 사람으로 발견했던 패턴"을 실제로 짚어내는지 확인한다:

시나리오 A: 특정 카테고리에서만 안정적으로 재시도가 튀는 경우
            (P2-29/30류 - 노이즈가 아니라 특정 주제에 국한된 구조적 문제)
시나리오 B: 대부분의 문항에서 재시도·확신도저하가 광범위하게 발생하는 경우
            (R/S절 DYNAMIC_TOPK×all_or_nothing 회귀류 - 전면적 심각한 문제)
시나리오 C: 평범한 정상 운영일 (재시도율 낮고 카테고리별 편중 없음) -
            여기서 억지로 문제를 지어내지 않는지(과잉경보 방지)가 핵심 확인사항

성공기준: A는 "특정 카테고리 국한" 문제로, B는 "광범위한" 문제로 구분해서
언급하고, C는 문제를 지어내지 않고 "특이사항 없음" 계열로 답해야 한다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_ops_monitor_pilot
"""
import sys
import os

sys.path.insert(0, os.getcwd())

from AI.ops_monitor import aggregate_stats, generate_ops_report  # noqa: E402


def _trace(text, route, domain, category, rewrite=0, regenerate=0, confidence="sufficient", halluc_ok=True, answer_ok=True):
    return {
        "input": {"text": text},
        "output": {
            "text": text, "route": route,
            "cls": {"domain": domain, "category": category},
            "rewrite_count": rewrite, "regenerate_count": regenerate,
            "answer_confidence": confidence,
            "hallucination_ok": halluc_ok, "answer_ok": answer_ok,
        },
    }


def build_scenario_a() -> list[dict]:
    """'파워퓨즈 옥외/옥내' 카테고리(기타)에서만 안정적으로 재시도가 튀고,
    나머지 카테고리는 다 정상인 상황."""
    traces = []
    # 문제 카테고리: 8건 전부 재시도 발생
    for i in range(8):
        traces.append(_trace(
            f"파워퓨즈 옥외용을 옥내에서 써도 되나요? (변형 {i})", "rag", "technical", "기타",
            rewrite=2, regenerate=1, confidence="partial", halluc_ok=False,
        ))
    # 나머지 카테고리: 22건 전부 정상
    categories = [("기술지원", "technical"), ("교육", "admin"), ("경력회원", "admin"), ("공제사업", "admin")]
    for i in range(22):
        cat, dom = categories[i % len(categories)]
        traces.append(_trace(f"정상 질문 {i}", "rag", dom, cat, confidence="sufficient"))
    return traces


def build_scenario_b() -> list[dict]:
    """DYNAMIC_TOPK x all_or_nothing 회귀 재현 - 대부분(80%)의 문항에서
    재시도 소진 + confidence insufficient가 카테고리 무관하게 광범위하게 발생."""
    traces = []
    categories = [("기술지원", "technical"), ("교육", "admin"), ("경력회원", "admin"),
                  ("공제사업", "admin"), ("전기안전관리자", "admin")]
    for i in range(30):
        cat, dom = categories[i % len(categories)]
        if i < 24:  # 80%가 광범위하게 문제
            traces.append(_trace(
                f"문의 {i}", "rag", dom, cat, rewrite=2, regenerate=0, confidence="insufficient",
            ))
        else:
            traces.append(_trace(f"문의 {i}", "rag", dom, cat, confidence="sufficient"))
    return traces


def build_scenario_c() -> list[dict]:
    """평범한 정상 운영일 - 재시도율이 확실히 낮고(약 6.7%, 2/30), 카테고리별
    편중도 없게 결정적으로 구성(랜덤 대신 고정 - 우연히 시나리오 A와 비슷한
    비율이 나오는 걸 방지)."""
    traces = []
    categories = [("기술지원", "technical"), ("교육", "admin"), ("경력회원", "admin"),
                  ("공제사업", "admin"), ("전기안전관리자", "admin"), ("기타", "admin")]
    for i in range(30):
        cat, dom = categories[i % len(categories)]
        # 30건 중 딱 2건만 가볍게 재시도(각기 다른 카테고리에 1건씩 -> 편중 없음)
        if i in (3, 17):
            traces.append(_trace(f"문의 {i}", "rag", dom, cat, rewrite=1, confidence="partial"))
        else:
            traces.append(_trace(f"문의 {i}", "rag", dom, cat, confidence="sufficient"))
    return traces


def run():
    scenarios = [
        ("A: 특정 카테고리(파워퓨즈/기타) 국한 문제", build_scenario_a()),
        ("B: 광범위한 전면 회귀", build_scenario_b()),
        ("C: 평범한 정상 운영일 (과잉경보 방지 확인)", build_scenario_c()),
    ]

    for name, traces in scenarios:
        print("=" * 80)
        print(f"시나리오 {name}")
        print("=" * 80)
        stats = aggregate_stats(traces)
        print(f"집계: 재시도율={stats['retry_rate']:.1%}, 근거불일치율={stats['hallucination_fail_rate']:.1%}, "
              f"카테고리분포={stats['category_dist']}")
        print()
        report = generate_ops_report(stats)
        print("생성된 리포트:")
        print(report)
        print()


if __name__ == "__main__":
    run()