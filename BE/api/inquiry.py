"""
문의 처리 라우터.

설계 원칙: 사용자는 문의를 등록하면 '접수 확인'만 받는다.
AI가 만든 답변 초안은 담당자가 검토·승인(reviewed=True)하기 전까지
사용자에게 노출되지 않는다. (계획서의 '담당자 검토 후 발송' 원칙을
API 레벨에서 강제한 것 — 초안이 그대로 새 나가지 않게 한다.)

엔드포인트:
  POST   /api/inquiry             문의 등록 (로그인 필요) → 접수 확인만 반환
  GET    /api/inquiry/my          내 문의 목록 (로그인 필요, user_id로 자동 필터)
  GET    /api/inquiry/my/{id}     내 문의 상세
  GET    /api/inquiry/pending     검토 대기 큐 (담당자 전용)
  PATCH  /api/inquiry/{id}/review 검토·승인 (담당자 전용)
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
    """검토 전이면 답변을 숨기고 pending, 검토 후면 최종답변과 함께 answered."""
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
    """
    문의를 등록한다. AI 처리는 즉시 이루어지지만, 그 결과(분류·답변 등)는
    이 응답에 담기지 않는다 — 담당자 검토 후 /my 에서 확인해야 한다.
    """
    response = process_inquiry(req.text)
    try:
        record = crud.save_inquiry(db, response, user_id=int(user["sub"]))
    except Exception:
        # DB가 유일한 전달 경로이므로, 저장 실패는 사용자에게 반드시 알려야 한다
        # (예전처럼 조용히 넘어가면 사용자가 낸 문의가 그냥 사라지는 셈이 됨)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="문의 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        )
    return InquirySubmitResponse(id=record.id, created_at=record.created_at.isoformat())


@router.get("/inquiry/my", response_model=list[InquiryStatusResponse])
def list_my_inquiries(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """내 문의 목록. 키워드 검색이 아니라 로그인한 사용자 기준으로 자동 필터링된다."""
    records = crud.get_user_inquiries(db, user_id=int(user["sub"]))
    return [_to_status_response(r) for r in records]


@router.get("/inquiry/my/{inquiry_id}", response_model=InquiryStatusResponse)
def get_my_inquiry(
    inquiry_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    """내 문의 상세 1건. 다른 사람 문의는 조회할 수 없다."""
    record = crud.get_user_inquiry_by_id(db, inquiry_id, user_id=int(user["sub"]))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)


@router.get("/inquiry/pending", response_model=list[PendingInquiryResponse])
def list_pending_inquiries(db: Session = Depends(get_db), user: dict = Depends(require_staff)):
    """검토 대기 큐 (담당자 이상). 검토 판단에 필요한 분류·근거·AI상태를 모두 포함한다."""
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
            department=r.department,
            priority=r.priority,
            answer_draft=r.answer_draft,
            answer_confidence=r.answer_confidence,
            retrieved=r.retrieved_docs or [],
            used_llm=r.used_llm,
            llm_error=r.llm_error,
        )
        for r in records
    ]


@router.patch("/inquiry/{inquiry_id}/rule", response_model=InquiryStatusResponse)
def update_inquiry_rule(
    inquiry_id: int,
    req: RuleUpdateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_master),
):
    """AI가 잘못 배정한 부서/우선순위를 최고관리자가 재배정한다."""
    record = crud.update_rule(db, inquiry_id, priority=req.priority, department=req.department)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)


@router.patch("/inquiry/{inquiry_id}/review", response_model=InquiryStatusResponse)
def review_inquiry(
    inquiry_id: int,
    req: ReviewRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_staff),
):
    """담당자가 문의를 검토·승인한다. final_answer 생략 시 AI 초안을 그대로 승인."""
    record = crud.mark_reviewed(db, inquiry_id, reviewed_by=user["email"], final_answer=req.final_answer)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="문의를 찾을 수 없습니다.")
    return _to_status_response(record)