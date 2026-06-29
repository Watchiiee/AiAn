"""
핵심 파이프라인: 분류 → 룰 → RAG 검색 → 답변 생성.
계획서 4번 '시스템 흐름'의 2~5단계를 한 함수로 묶는다.
(1단계 입력변환=OCR/STT는 3주차, 6단계 검토·발송은 FE 몫)

여기가 BE 와 AI 가 만나는 지점이다:
  - 분류·검색·생성  → AI 패키지
  - 룰·스키마·설정  → BE 패키지
"""
from BE.core.config import settings
from BE.core.schemas import InquiryResponse
from BE.rules.rule_engine import apply_rules
from AI.classifier.classifier import classify
from AI.rag.retriever import retrieve
from AI.rag.generator import generate


def process_inquiry(text: str) -> InquiryResponse:
    cls = classify(text)                       # 1. 분류   (AI)
    rule = apply_rules(text, cls)              # 2. 룰     (BE)
    docs = retrieve(text, cls)                 # 3. 검색   (AI)
    answer = generate(text, cls, rule, docs)   # 4. 답변   (AI)

    return InquiryResponse(
        original_text=text,
        classification=cls,
        rule=rule,
        retrieved=docs,
        answer_draft=answer,
        used_llm=settings.has_api_key,
    )