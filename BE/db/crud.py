"""
문의 이력 DB 조작 함수 모음.

원칙: DB 저장 자체는 부가 기능처럼 보이지만, 이제 답변을 사용자에게
돌려주는 유일한 경로가 DB(조회 API)이므로 저장 실패는 반드시
호출부에 알려야 한다 (예전처럼 조용히 넘어가면 사용자가 낸 문의가
사라지는 셈이 됨).
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from BE.core.schemas import InquiryResponse
from BE.db.models import InquiryRecord

logger = logging.getLogger(__name__)


def save_inquiry(db: Session, response: InquiryResponse, user_id: int) -> InquiryRecord:
    """처리 결과를 inquiries 테이블에 저장하고, 저장된 레코드를 돌려준다.
    저장이 실패하면 예외를 그대로 올린다 (호출부가 사용자에게 에러를 알려야 함)."""
    record = InquiryRecord(
        user_id=user_id,
        original_text=response.original_text,
        inquiry_type=response.classification.type.value,
        key_request=response.classification.key_request,
        domain=response.classification.domain.value,
        confidence=response.classification.confidence,
        department=response.rule.department,
        priority=response.rule.priority,
        category=response.classification.category.value,
        department_certain=response.rule.department_certain,
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


def get_user_inquiries(db: Session, user_id: int) -> list[InquiryRecord]:
    """특정 사용자가 등록한 문의 전체를 최신순으로."""
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.user_id == user_id)
        .order_by(InquiryRecord.created_at.desc())
        .all()
    )


def get_user_inquiry_by_id(db: Session, inquiry_id: int, user_id: int) -> InquiryRecord | None:
    """특정 사용자 소유의 문의 1건 (다른 사람 문의는 못 보게 user_id로 제한)."""
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.id == inquiry_id, InquiryRecord.user_id == user_id)
        .first()
    )


def get_pending_inquiries(db: Session) -> list[InquiryRecord]:
    """담당자 검토 대기 중인 문의 전체 (담당자 전용 큐)."""
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.reviewed == False)  # noqa: E712
        .order_by(InquiryRecord.created_at.asc())
        .all()
    )


def mark_reviewed(
    db: Session, inquiry_id: int, reviewed_by: str, final_answer: str | None = None
) -> InquiryRecord | None:
    """담당자가 문의를 검토·승인 처리한다. final_answer를 주면 답변을 그걸로 교체."""
    record = db.query(InquiryRecord).filter(InquiryRecord.id == inquiry_id).first()
    if record is None:
        return None
    record.reviewed = True
    record.reviewed_by = reviewed_by
    record.reviewed_at = datetime.now(timezone.utc)
    if final_answer:
        record.final_answer = final_answer
    db.commit()
    db.refresh(record)
    return record


def update_rule(
    db: Session, inquiry_id: int, priority: str | None = None, department: str | None = None
) -> InquiryRecord | None:
    """AI 분류(룰) 결과가 틀렸을 때 최고관리자가 부서/우선순위를 재배정한다."""
    record = db.query(InquiryRecord).filter(InquiryRecord.id == inquiry_id).first()
    if record is None:
        return None
    if priority is not None:
        record.priority = priority
    if department is not None:
        record.department = department
        record.department_certain = True  # 사람이 직접 확정했으므로 더는 불확실 아님
    db.commit()
    db.refresh(record)
    return record