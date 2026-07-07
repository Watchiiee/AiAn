"""
4단계: 답변 초안 생성 + 확신도 판정.

동작:
  - 검색 최고 score < 임계값(config.no_evidence_threshold): LLM 안 부르고 바로
    insufficient (명백히 근거 없는 질문을 싸게 차단)
  - 그 이상: LLM이 답변 + 확신도(sufficient/partial/insufficient)를 JSON으로 판단
  - 키 없음: 템플릿 폴백 / LLM 실패(429·503 등): LLMError 를 파이프라인으로 올려보냄

반환: (answer_text, AnswerConfidence)
프롬프트는 AI/prompts.py. 원칙: 근거에 없는 내용은 지어내지 말 것.
"""
import json
from AI.llm import call_llm
from AI.prompts import GENERATOR_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, RuleResult, RetrievedDoc, AnswerConfidence


def _format_docs(docs: list[RetrievedDoc]) -> str:
    return "\n".join(f"- ({d.source}) {d.content}" for d in docs)


def _top_score(docs: list[RetrievedDoc]) -> float:
    return max((d.score for d in docs), default=0.0)


def _no_evidence_answer(rule: RuleResult) -> str:
    return (
        "안녕하세요. 문의하신 내용은 현재 보유한 자료에서 정확한 근거를 찾기 어렵습니다.\n\n"
        f"정확한 안내를 위해 {rule.department}에서 확인 후 회신드리겠습니다. 감사합니다."
    )


def fallback_answer(text: str, cls: Classification, rule: RuleResult,
                    docs: list[RetrievedDoc], reason: str | None = None) -> str:
    """LLM 없이(또는 실패 시) 근거 문서를 끼운 임시 답변."""
    body = docs[0].content if docs else "담당 부서에서 확인 후 회신드리겠습니다."
    note = (
        f"(※ 자동 답변 생성 실패: {reason} — 아래는 근거 문서 기반 임시 안내입니다)\n\n"
        if reason else
        "(※ 더미 답변 — API 키 연결 시 LLM이 작성합니다)\n\n"
    )
    return (
        f"{note}"
        f"안녕하세요. 문의하신 '{cls.key_request}' 건에 대해 안내드립니다.\n\n"
        f"{body}\n\n"
        f"추가 문의는 {rule.department}으로 연락 주시기 바랍니다. 감사합니다."
    )


def generate(text: str, cls: Classification, rule: RuleResult,
             docs: list[RetrievedDoc]) -> tuple[str, AnswerConfidence]:
    """
    답변 초안 + 확신도를 반환한다.
    LLM 호출 실패(LLMError)는 여기서 잡지 않고 파이프라인으로 올려보낸다.
    """
    # (1) score 바닥 → LLM 부를 것도 없이 근거 없음 처리
    if _top_score(docs) < settings.no_evidence_threshold:
        return _no_evidence_answer(rule), AnswerConfidence.INSUFFICIENT

    # (2) LLM에 답변 + 확신도 판단 요청
    docs_text = _format_docs(docs)
    user = (
        f"[문의 유형] {cls.type.value}\n"
        f"[핵심 요청] {cls.key_request}\n"
        f"[담당 부서] {rule.department}\n"
        f"[원문] {text}\n\n"
        f"[근거 문서]\n{docs_text}\n\n"
        f"위 근거로 답할 수 있는지 판단하고, 지정된 JSON 형식으로 답변 초안을 작성하라."
    )
    raw = call_llm(settings.generator_model, GENERATOR_SYSTEM, user, max_tokens=1024)

    if raw is None:  # 키 없음 → 템플릿 폴백
        return fallback_answer(text, cls, rule, docs), AnswerConfidence.SUFFICIENT

    return _parse(raw, rule)


def _parse(raw: str, rule: RuleResult) -> tuple[str, AnswerConfidence]:
    """LLM의 JSON 응답을 (답변, 확신도)로 파싱. 실패 시 원문을 답변으로 쓰고 partial."""
    try:
        data = json.loads(raw)
        answer = (data.get("answer") or "").strip()
        conf = AnswerConfidence(data.get("confidence", "sufficient"))
        if not answer:
            raise ValueError("빈 답변")
        return answer, conf
    except (json.JSONDecodeError, ValueError, KeyError):
        # JSON이 아니면 모델이 그냥 답변만 준 것 → 원문을 답변으로 쓰되 확인 필요로 표시
        return raw.strip(), AnswerConfidence.PARTIAL