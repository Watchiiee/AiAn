"""문의 처리 라우터."""
from fastapi import APIRouter
from BE.core.schemas import InquiryRequest, InquiryResponse
from BE.api.pipeline import process_inquiry

router = APIRouter(prefix="/api", tags=["inquiry"])


@router.post("/inquiry", response_model=InquiryResponse)
def create_inquiry(req: InquiryRequest):
    """텍스트 민원 한 건을 받아 분류→룰→RAG→답변초안까지 처리한다."""
    return process_inquiry(req.text)