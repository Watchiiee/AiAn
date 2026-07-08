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


def process_inquiry(text: str, db=None) -> InquiryResponse:
    """
    문의 하나를 처리한다.
    db(Session)를 주면 처리 결과를 inquiries 테이블에 저장한다.
    (db=None 이면 저장을 건너뛴다 — 테스트나 저장이 필요 없는 호출에 사용)
    """
    cls = classify(text)                       # 1. 분류   (AI, 실패 시 내부 폴백)
    rule = apply_rules(text, cls)              # 2. 룰     (BE)
    docs = retrieve(text, cls)                 # 3. 검색   (AI)

    llm_error = None
    from BE.core.schemas import AnswerConfidence
    try:
        answer, answer_confidence = generate(text, cls, rule, docs)   # 4. 답변 (AI)
    except LLMError as e:
        # 429/503 등 → 시스템 죽이지 않고 임시 답변 + 사유 표시
        llm_error = str(e)
        answer = fallback_answer(text, cls, rule, docs, reason=llm_error)
        answer_confidence = AnswerConfidence.PARTIAL

    response = InquiryResponse(
        original_text=text,
        classification=cls,
        rule=rule,
        retrieved=docs,
        answer_draft=answer,
        answer_confidence=answer_confidence,
        used_llm=settings.has_api_key and llm_error is None,
        llm_error=llm_error,
    )

    if db is not None:
        from BE.db.crud import save_inquiry
        save_inquiry(db, response)  # 실패해도 조용히 넘어감 (crud.py 참고)

    return response