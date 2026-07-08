"""
DB 테이블 모델.

- InquiryRecord: 처리한 문의 이력 (분류·근거·답변·검토 여부까지 기록)
- User: 회원 정보 (일반/담당자). 인증은 JWT 방식이라 세션 테이블은 두지 않는다.
  (자주 조회되는 인증 관련 캐시가 필요해지면 Redis를 별도로 쓴다 — DB 테이블 아님)
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Enum, ForeignKey
from BE.db.database import Base


class InquiryRecord(Base):
    """처리한 민원 문의 1건의 이력."""
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # 어떤 사용자가 등록했는지 (내 문의 조회에 사용, 키워드 검색 대신 로그인 사용자로 자동 필터링)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # 원문·분류 결과
    original_text = Column(String, nullable=False)
    inquiry_type = Column(String, nullable=False)       # 예: 경력인증, 신청 ...
    key_request = Column(String, nullable=True)          # 핵심 요청 한 줄 요약
    domain = Column(String, nullable=False)             # admin / technical
    confidence = Column(Float, nullable=False)

    # 룰 적용 결과
    department = Column(String, nullable=False)
    priority = Column(String, nullable=False)

    # 답변
    answer_draft = Column(String, nullable=False)
    answer_confidence = Column(String, nullable=False)  # sufficient/partial/insufficient
    retrieved_docs = Column(JSON, nullable=True)         # [{content, source, score}, ...]

    # LLM 호출 상태
    used_llm = Column(Boolean, default=False)
    llm_error = Column(String, nullable=True)

    # 담당자 검토 (초기값은 미검토)
    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String, nullable=True)          # 검토한 담당자 이메일/이름
    reviewed_at = Column(DateTime, nullable=True)
    final_answer = Column(String, nullable=True)         # 담당자가 수정한 최종 답변 (없으면 초안 그대로)


class UserRole(str, enum.Enum):
    GENERAL = "general"      # 일반 사용자
    STAFF = "staff"          # 담당자 (검토·승인)
    MASTER = "master"        # 최고관리자 (담당자 권한 + 부서/우선순위 재배정 등)


class User(Base):
    """회원 정보. 비밀번호는 반드시 해시로 저장한다 (평문 저장 금지)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.GENERAL, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))