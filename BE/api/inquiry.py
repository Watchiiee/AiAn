"""
문의 처리 라우터.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from BE.core.schemas import (
    InquiryRequest, InquirySubmitResponse, InquiryStatusResponse, InquiryStatus,
    ReviewRequest, PendingInquiryResponse, RuleUpdateRequest, DeptChangeRequest,
)
from BE.api.pipeline import process_inquiry
from BE.db.database import get_db
from BE.db.models import InquiryRecord
from BE.db import crud
from BE.core.deps import get_current_user, require_staff, require_master

router = APIRouter(prefix="/api", tags=["inquiry"])


def _to_status_response(record: InquiryRecord) -> InquiryStatusResponse:
    if record.reviewed:
        return InquiryStatusResponse(
            id=record.id,
            created_at=record.created_at.isoformat(),
            original_text=record.original_text,
            department=record.department,
            priority=record.priority,
            status=InquiryStatus.ANSWERED,
            answer=record.final_answer or record.answer_draft,
        )
    return InquiryStatusResponse(
        id=record.id,
        created_at=record.created_at.isoformat(),
        original_text=record.original_text,
        department=record.department,
        priority=record.priority,
        status=InquiryStatus.PENDING,
        answer=None,
    )


@router.post("/inquiry", response_model=InquirySubmitResponse, status_code=status.HTTP_201_CREATED)
def create_inquiry(
    req: InquiryRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    response = process_inquiry(req.text)
    try:
        record = crud.save_inquiry(db, response, user_id=int(user["sub"]))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="문의 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        )
    return InquirySubmitResponse(id=record.id, created_at=record.created_at.isoformat())


@router.get("/inquiry/my", response_model=list[InquiryStatusResponse])
def list_my_inquiries(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    records = crud.get_user_inquiries(db, user_id=int(user["sub"]))
    return [_to_status_response(r) for r in records]


@router.get("/inquiry/my/{inquiry_id}", response_model=InquiryStatusResponse)
def get_my_inquiry(
    inquiry_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    record = crud.get_user_inquiry_by_id(db, inquiry_id, user_id=int(user["sub"]))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)


def _to_pending_response(r: InquiryRecord) -> PendingInquiryResponse:
    return PendingInquiryResponse(
        id=r.id,
        created_at=r.created_at.isoformat(),
        original_text=r.original_text,
        inquiry_type=r.inquiry_type,
        key_request=r.key_request,
        confidence=r.confidence,
        domain=r.domain,
        category=r.category,
        department=r.department,
        department_certain=r.department_certain,
        department_note=r.department_note,
        urgent_reason=r.urgent_reason,
        priority=r.priority,
        answer_draft=r.answer_draft,
        answer_confidence=r.answer_confidence,
        retrieved=r.retrieved_docs or [],
        used_llm=r.used_llm,
        llm_error=r.llm_error,
        dept_change_requested=r.dept_change_requested,
        dept_change_reason=r.dept_change_reason,
        dept_change_suggested=r.dept_change_suggested,
        dept_change_requested_by=r.dept_change_requested_by,
    )


@router.get("/inquiry/pending", response_model=list[PendingInquiryResponse])
def list_pending_inquiries(db: Session = Depends(get_db), user: dict = Depends(require_staff)):
    """
    master는 전체 부서 큐를 본다(재배정 판단을 위해 필요). 일반 staff는 자기
    부서로 배정된 것만 본다. staff인데 department가 아직 지정 안 됐으면
    (운영자가 SQL로 role만 올리고 department는 안 지정한 경우) 아무 부서
    문의도 잘못 보여주지 않도록 안전하게 빈 목록을 반환한다.
    """
    if user.get("role") == "master":
        records = crud.get_pending_inquiries(db)
    else:
        dept = user.get("department")
        if not dept:
            return []
        records = crud.get_pending_inquiries(db, department=dept)
    return [_to_pending_response(r) for r in records]


@router.patch("/inquiry/{inquiry_id}/review", response_model=InquiryStatusResponse)
def review_inquiry(
    inquiry_id: int,
    req: ReviewRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_staff),
):
    record = crud.mark_reviewed(db, inquiry_id, reviewed_by=user["email"], final_answer=req.final_answer)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)


@router.patch("/inquiry/{inquiry_id}/request-department-change", response_model=PendingInquiryResponse)
def request_department_change(
    inquiry_id: int,
    req: DeptChangeRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_staff),
):
    """
    staff가 "이 문의는 우리 부서 업무가 아닌 것 같다"고 재배정을 요청.
    실제 재배정 권한은 master에게만 있으므로(PATCH /rule 참고), 이 엔드포인트는
    부서를 직접 바꾸지 않고 검토대기 큐(GET /pending)에 요청 표시만 남긴다.
    master가 큐에서 이 표시를 보고 PATCH /rule로 실제 재배정하면, 그 순간
    이 요청 표시는 자동으로 해소(초기화)된다(crud.update_rule 참고).
    """
    record = crud.request_department_change(
        db, inquiry_id, reason=req.reason, requested_by=user["email"],
        suggested_department=req.suggested_department,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="문의를 찾을 수 없거나, 이미 검토완료된 문의라 요청할 수 없습니다.",
        )
    return _to_pending_response(record)


@router.patch("/inquiry/{inquiry_id}/rule", response_model=PendingInquiryResponse)
def update_inquiry_rule(
    inquiry_id: int,
    req: RuleUpdateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_master),
):
    record = crud.update_rule(db, inquiry_id, priority=req.priority, department=req.department)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_pending_response(record)