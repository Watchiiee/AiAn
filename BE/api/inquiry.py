"""
문의 처리 라우터.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from BE.core.schemas import (
    InquiryRequest, InquirySubmitResponse, InquiryStatusResponse, InquiryStatus,
    ReviewRequest, PendingInquiryResponse, RuleUpdateRequest,
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


@router.get("/inquiry/pending", response_model=list[PendingInquiryResponse])
def list_pending_inquiries(db: Session = Depends(get_db), user: dict = Depends(require_staff)):
    records = crud.get_pending_inquiries(db)
    return [
        PendingInquiryResponse(
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
        )
        for r in records
    ]


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


@router.patch("/inquiry/{inquiry_id}/rule", response_model=InquiryStatusResponse)
def update_inquiry_rule(
    inquiry_id: int,
    req: RuleUpdateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_master),
):
    record = crud.update_rule(db, inquiry_id, priority=req.priority, department=req.department)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)