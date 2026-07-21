import logging
from datetime import datetime, timezone

from sqlalchemy import case
from sqlalchemy.orm import Session

from BE.core.schemas import InquiryResponse
from BE.db.models import InquiryRecord

logger = logging.getLogger(__name__)


def save_inquiry(db: Session, response: InquiryResponse, user_id: int) -> InquiryRecord:
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
        department_note=response.rule.department_note,
        urgent_reason=response.rule.urgent_reason,
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
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.user_id == user_id)
        .order_by(InquiryRecord.created_at.desc())
        .all()
    )


def get_user_inquiry_by_id(db: Session, inquiry_id: int, user_id: int) -> InquiryRecord | None:
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.id == inquiry_id, InquiryRecord.user_id == user_id)
        .first()
    )


def get_pending_inquiries(db: Session) -> list[InquiryRecord]:
    """
    검토 대기 큐. priority='긴급'인 건을 최상단에 고정하고, 그 안에서는(그리고
    나머지 안에서도) 오래 기다린 순으로 정렬한다.

    [설계 변경] 과거엔 긴급 민원이 RAG를 건너뛰고 별도 안내문만 담긴 채 바로
    들어왔는데, 이제는 긴급 여부와 무관하게 모든 문의가 RAG를 통과해 초안이
    붙은 채로 이 큐에 들어온다(BE/api/pipeline.py 참고) — "초안이 있는지"와
    "얼마나 먼저 보이는지"를 분리한 것이며, 이 정렬이 그 "먼저 보이기"를
    담당한다.
    """
    urgent_first = case((InquiryRecord.priority == "긴급", 0), else_=1)
    return (
        db.query(InquiryRecord)
        .filter(InquiryRecord.reviewed == False)  # noqa: E712
        .order_by(urgent_first, InquiryRecord.created_at.asc())
        .all()
    )


def mark_reviewed(
    db: Session, inquiry_id: int, reviewed_by: str, final_answer: str | None = None
) -> InquiryRecord | None:
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
    record = db.query(InquiryRecord).filter(InquiryRecord.id == inquiry_id).first()
    if record is None:
        return None
    if priority is not None:
        record.priority = priority
    if department is not None:
        record.department = department
        record.department_certain = True
    db.commit()
    db.refresh(record)
    return record