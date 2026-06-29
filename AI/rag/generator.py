"""
4단계: 답변 초안 생성.
검색된 근거 문서를 바탕으로 LLM이 답변 초안을 작성한다.
키가 없으면 근거를 끼워넣은 템플릿으로 폴백 (1주차 데모용).
프롬프트는 AI/prompts.py 에 분리해 두었다.

원칙: 근거에 없는 내용을 지어내지 말 것. 담당자가 검토·수정해 발송하는 '초안'이다.
"""
from AI.llm import call_llm
from AI.prompts import GENERATOR_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, RuleResult, RetrievedDoc


def _format_docs(docs: list[RetrievedDoc]) -> str:
    return "\n".join(f"- ({d.source}) {d.content}" for d in docs)


def generate(text: str, cls: Classification, rule: RuleResult,
             docs: list[RetrievedDoc]) -> str:
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
        return (
            f"안녕하세요. 문의하신 '{cls.key_request}' 건에 대해 안내드립니다.\n\n"
            f"{docs[0].content if docs else '담당 부서에서 확인 후 회신드리겠습니다.'}\n\n"
            f"추가 문의는 {rule.department}으로 연락 주시기 바랍니다. 감사합니다.\n\n"
            f"(※ 더미 답변 — API 키 연결 시 LLM이 작성합니다)"
        )
    return answer