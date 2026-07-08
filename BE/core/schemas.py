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


# --- 도메인 (검색 라우팅 키) ---
class Domain(str, Enum):
    """질의 도메인. 검색할 지식베이스 컬렉션을 결정하는 라우팅 키."""
    ADMIN = "admin"          # 행정·절차 (신고·발급·수수료·자격 등)
    TECHNICAL = "technical"  # 기술 질의 (발전기·변압기·설비 등)


# --- 1단계: 분류 결과 ---
class Classification(BaseModel):
    type: InquiryType
    key_request: str = Field(..., description="문의의 핵심 요청 한 줄 요약")
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    domain: Domain = Field(Domain.ADMIN, description="질의 도메인 (검색 라우팅용)")


# --- 2단계: 룰 적용 결과 ---
class RuleResult(BaseModel):
    priority: str = Field(..., description="긴급/높음/보통")
    department: str = Field(..., description="담당 부서")


class AnswerConfidence(str, Enum):
    """답변 확신도. 근거 문서로 얼마나 답할 수 있는지 나타낸다 (프론트 배지용)."""
    SUFFICIENT = "sufficient"      # 근거 충분 → 자신 있게 답변
    PARTIAL = "partial"            # 부분적 → 근접 답변 + 확인 필요
    INSUFFICIENT = "insufficient"  # 근거 부족 → 답 못 함, 담당부서 안내


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
    answer_confidence: AnswerConfidence = Field(
        AnswerConfidence.SUFFICIENT,
        description="답변 확신도: sufficient(충분)/partial(확인필요)/insufficient(근거부족)"
    )
    used_llm: bool = Field(..., description="실제 LLM 호출 성공 여부 (False면 더미/폴백)")
    llm_error: str | None = Field(None, description="LLM 호출 실패 시 짧은 사유 (없으면 None)")


# --- 인증: 회원가입/로그인 ---
class UserRoleSchema(str, Enum):
    GENERAL = "general"
    STAFF = "staff"
    MASTER = "master"


class RegisterRequest(BaseModel):
    """일반 회원가입 요청. role은 받지 않는다 — 가입은 항상 general이며,
    staff/master 권한은 운영자가 DB에서 직접 부여한다."""
    email: str
    password: str = Field(..., min_length=8, description="8자 이상")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRoleSchema


class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRoleSchema

    class Config:
        from_attributes = True


# --- 문의 접수/조회 (사용자에게 답변을 바로 보여주지 않고, 접수만 확인시켜준다) ---
class InquirySubmitResponse(BaseModel):
    """POST /api/inquiry 응답. 분류·답변 등 내부 처리결과는 담지 않는다."""
    id: int
    message: str = "정상적으로 접수되었습니다."
    created_at: str


class InquiryStatus(str, Enum):
    PENDING = "pending"    # 담당자 검토 전 (사용자에게 답변 미공개)
    ANSWERED = "answered"  # 담당자 검토·승인 완료 (답변 공개)


class InquiryStatusResponse(BaseModel):
    """GET /api/inquiry/my, /my/{id} 응답. 검토 전엔 답변을 담지 않는다."""
    id: int
    created_at: str
    original_text: str
    department: str
    priority: str
    status: InquiryStatus
    answer: str | None = None  # pending이면 None


class ReviewRequest(BaseModel):
    """담당자가 문의를 검토·승인할 때. final_answer 를 안 주면 AI 초안을 그대로 승인."""
    final_answer: str | None = None


class PendingInquiryResponse(BaseModel):
    """GET /api/inquiry/pending (담당자용 검토 대기 큐) 응답 항목.
    담당자가 검토 판단을 하려면 분류·근거·AI 처리상태까지 다 봐야 하므로
    v1 InquiryResponse 수준의 정보를 그대로 포함한다."""
    id: int
    created_at: str
    original_text: str
    inquiry_type: str
    key_request: str | None = None
    confidence: float
    domain: str
    department: str
    priority: str
    answer_draft: str
    answer_confidence: AnswerConfidence
    retrieved: list[RetrievedDoc] = []
    used_llm: bool
    llm_error: str | None = None


class RuleUpdateRequest(BaseModel):
    """담당자의 AI 분류가 틀렸을 때 최고관리자가 부서/우선순위를 재배정."""
    priority: str | None = None
    department: str | None = None