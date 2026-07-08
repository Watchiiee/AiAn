"""
문의 처리 이력을 DB에 저장.

원칙: DB 저장은 부가 기능이다. 저장이 실패해도(DB 장애 등)
사용자에게 준 응답 자체는 이미 만들어졌으니 API가 죽으면 안 된다.
그래서 저장 실패는 조용히 로그만 남기고 넘어간다.
"""
import logging
from sqlalchemy.orm import Session

from BE.core.schemas import InquiryResponse
from BE.db.models import InquiryRecord

logger = logging.getLogger(__name__)


def save_inquiry(db: Session, response: InquiryResponse) -> InquiryRecord | None:
    """처리 결과를 inquiries 테이블에 저장. 실패해도 예외를 올리지 않는다."""
    try:
        record = InquiryRecord(
            original_text=response.original_text,
            inquiry_type=response.classification.type.value,
            domain=response.classification.domain.value,
            confidence=response.classification.confidence,
            department=response.rule.department,
            priority=response.rule.priority,
            answer_draft=response.answer_draft,
            answer_confidence=response.answer_confidence.value,
            retrieved_docs=[d.model_dump() for d in response.retrieved],
            used_llm=response.used_llm,
            llm_error=response.llm_error,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        # DB 저장 실패는 사용자 응답에 영향 주면 안 됨 (부가 기능이므로 조용히 넘어감)
        logger.exception("문의 이력 저장 실패 (사용자 응답에는 영향 없음)")
        db.rollback()
        return None