"""
파이프라인을 흐르는 데이터의 모양(스키마)을 정의한다.
BE 와 AI 양쪽에서 함께 쓰는 '계약'이라 BE/core 에 둔다.
계획서 6번 '문의 유형' 표를 그대로 코드로 옮긴 것이 InquiryType.
"""
from enum import Enum
from pydantic import BaseModel, Field


class InquiryType(str, Enum):
    """계획서 6번 문의 유형. 경력인증은 여러 유형 중 하나일 뿐임을 기억."""
    CAREER_CERT = "경력인증"
    APPLY = "신청"
    CHANGE = "변경"
    CANCEL_REFUND = "취소/환불"
    ERROR = "오류/장애"
    GENERAL = "일반문의"
    URGENT = "긴급문의"
    UNKNOWN = "미분류"  # 분류 실패 시 안전망


# --- 입력 ---
class InquiryRequest(BaseModel):
    text: str = Field(..., description="민원 문의 본문 (텍스트)")


# --- 1단계: 분류 결과 ---
class Classification(BaseModel):
    type: InquiryType
    key_request: str = Field(..., description="문의의 핵심 요청 한 줄 요약")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


# --- 2단계: 룰 적용 결과 ---
class RuleResult(BaseModel):
    priority: str = Field(..., description="긴급/높음/보통")
    department: str = Field(..., description="담당 부서")


# --- 3단계: RAG 검색된 근거 문서 한 조각 ---
class RetrievedDoc(BaseModel):
    content: str
    source: str = Field(..., description="출처 메타데이터 (답변 근거 표시용)")
    score: float = 0.0


# --- 최종 응답: 한 건의 처리 결과 전체 ---
class InquiryResponse(BaseModel):
    original_text: str
    classification: Classification
    rule: RuleResult
    retrieved: list[RetrievedDoc]
    answer_draft: str
    used_llm: bool = Field(..., description="실제 LLM 호출 여부 (False면 더미)")