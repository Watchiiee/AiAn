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


def get_pending_inquiries(db: Session, department: str | None = None) -> list[InquiryRecord]:
    """
    검토 대기 큐. priority='긴급'인 건을 최상단에 고정하고, 그 안에서는(그리고
    나머지 안에서도) 오래 기다린 순으로 정렬한다.

    department가 주어지면 그 부서로 배정된 문의만 반환한다(일반 staff용 —
    "우리 부서 것만 보인다"는 당연한 기대를 충족하기 위함). None이면 필터
    없이 전체를 반환한다(master용 — 전체 부서를 다 봐야 재배정 판단이 가능).

    [설계 변경] 과거엔 이 필터가 없어서 모든 staff 계정이 부서와 무관하게
    전체 큐를 봤음(실사용 중 발견된 버그, DECISION_LOG 참고).

    [설계 변경] 과거엔 긴급 민원이 RAG를 건너뛰고 별도 안내문만 담긴 채 바로
    들어왔는데, 이제는 긴급 여부와 무관하게 모든 문의가 RAG를 통과해 초안이
    붙은 채로 이 큐에 들어온다(BE/api/pipeline.py 참고) — "초안이 있는지"와
    "얼마나 먼저 보이는지"를 분리한 것이며, 이 정렬이 그 "먼저 보이기"를
    담당한다.
    """
    urgent_first = case((InquiryRecord.priority == "긴급", 0), else_=1)
    query = db.query(InquiryRecord).filter(InquiryRecord.reviewed == False)  # noqa: E712
    if department is not None:
        query = query.filter(InquiryRecord.department == department)
    return query.order_by(urgent_first, InquiryRecord.created_at.asc()).all()


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
        # master가 실제로 재배정했으니, staff가 남겨둔 변경요청은 해소된 것으로 처리
        record.dept_change_requested = False
        record.dept_change_reason = None
        record.dept_change_suggested = None
        record.dept_change_requested_by = None
        record.dept_change_requested_at = None
    db.commit()
    db.refresh(record)
    return record


def request_department_change(
    db: Session, inquiry_id: int, reason: str, requested_by: str, suggested_department: str | None = None,
) -> InquiryRecord | None:
    """
    staff가 "이 부서 아닌 것 같다"고 재배정을 요청. 실제 부서를 바꾸지는 않고
    (그 권한은 master에게만 있음, update_rule 참고) 검토대기 큐에 표시만 남긴다.
    이미 검토완료(reviewed=True)된 건은 요청을 받지 않는다 — 더 손댈 이유가 없다.
    """
    record = db.query(InquiryRecord).filter(InquiryRecord.id == inquiry_id).first()
    if record is None or record.reviewed:
        return None
    record.dept_change_requested = True
    record.dept_change_reason = reason
    record.dept_change_suggested = suggested_department
    record.dept_change_requested_by = requested_by
    record.dept_change_requested_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record