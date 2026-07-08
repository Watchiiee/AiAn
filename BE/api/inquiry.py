"""문의 처리 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from BE.core.schemas import InquiryRequest, InquiryResponse
from BE.api.pipeline import process_inquiry
from BE.db.database import get_db

router = APIRouter(prefix="/api", tags=["inquiry"])


@router.post("/inquiry", response_model=InquiryResponse)
def create_inquiry(req: InquiryRequest, db: Session = Depends(get_db)):
    """텍스트 민원 한 건을 받아 분류→룰→RAG→답변초안까지 처리하고, 이력을 DB에 저장한다."""
    return process_inquiry(req.text, db=db)