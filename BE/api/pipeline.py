"""
핵심 파이프라인: 분류 → 룰 → RAG 검색 → 답변 생성.
계획서 4번 '시스템 흐름'의 2~5단계를 한 함수로 묶는다.

LLM 호출이 실패해도(429/503 등) 시스템이 죽지 않게 처리한다:
  - 분류: classifier 내부에서 키워드로 조용히 폴백
  - 답변: 여기서 LLMError 를 잡아 fallback_answer(사유 포함)로 대체
  - 실패 사유는 응답의 llm_error 로 짧게 표시 (긴 로그 대신)
"""
from AI.llm import LLMError
from BE.core.config import settings
from BE.core.schemas import InquiryResponse
from BE.rules.rule_engine import apply_rules
from AI.classifier.classifier import classify
from AI.rag.retriever import retrieve
from AI.rag.generator import generate, fallback_answer


def process_inquiry(text: str) -> InquiryResponse:
    cls = classify(text)                       # 1. 분류   (AI, 실패 시 내부 폴백)
    rule = apply_rules(text, cls)              # 2. 룰     (BE)
    docs = retrieve(text, cls)                 # 3. 검색   (AI)

    llm_error = None
    try:
        answer = generate(text, cls, rule, docs)   # 4. 답변 (AI)
    except LLMError as e:
        # 429/503 등 → 시스템 죽이지 않고 임시 답변 + 사유 표시
        llm_error = str(e)
        answer = fallback_answer(text, cls, rule, docs, reason=llm_error)

    return InquiryResponse(
        original_text=text,
        classification=cls,
        rule=rule,
        retrieved=docs,
        answer_draft=answer,
        used_llm=settings.has_api_key and llm_error is None,
        llm_error=llm_error,
    )