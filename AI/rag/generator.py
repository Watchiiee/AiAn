"""
4단계: 답변 초안 생성.
검색된 근거 문서를 바탕으로 LLM이 답변 초안을 작성한다.

- 키가 없으면(호출 안 함): fallback_answer 로 근거를 끼운 템플릿 반환
- LLM 호출이 실패하면(429/503 등): LLMError 를 그대로 올려보냄
    → 파이프라인에서 잡아 fallback_answer(사유 포함) 로 대체하고, 시스템은 안 죽음

프롬프트는 AI/prompts.py 에 분리. 원칙: 근거에 없는 내용은 지어내지 말 것.
"""
from AI.llm import call_llm
from AI.prompts import GENERATOR_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, RuleResult, RetrievedDoc


def _format_docs(docs: list[RetrievedDoc]) -> str:
    return "\n".join(f"- ({d.source}) {d.content}" for d in docs)


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
             docs: list[RetrievedDoc]) -> str:
    """
    LLM으로 답변 초안 생성. 키가 없으면 템플릿 폴백.
    LLM 호출 실패(LLMError)는 여기서 잡지 않고 파이프라인으로 올려보낸다.
    """
    docs_text = _format_docs(docs)
    user = (
        f"[문의 유형] {cls.type.value}\n"
        f"[핵심 요청] {cls.key_request}\n"
        f"[담당 부서] {rule.department}\n"
        f"[원문] {text}\n\n"
        f"[근거 문서]\n{docs_text}\n\n"
        f"위 근거만으로 답변 초안을 작성하라."
    )

    answer = call_llm(settings.generator_model, GENERATOR_SYSTEM, user, max_tokens=1024)

    if answer is None:  # 키 없음 → 템플릿 폴백
        return fallback_answer(text, cls, rule, docs)
    return answer