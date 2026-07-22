import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Enum, ForeignKey
from BE.db.database import Base


class InquiryRecord(Base):
    """처리한 민원 문의 1건의 이력."""
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    original_text = Column(String, nullable=False)
    inquiry_type = Column(String, nullable=False)
    key_request = Column(String, nullable=True)
    domain = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    department = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    category = Column(String, nullable=True)
    department_certain = Column(Boolean, default=True)
    department_note = Column(String, nullable=True)
    urgent_reason = Column(String, nullable=True)

    answer_draft = Column(String, nullable=False)
    answer_confidence = Column(String, nullable=False)
    retrieved_docs = Column(JSON, nullable=True)

    used_llm = Column(Boolean, default=False)
    llm_error = Column(String, nullable=True)

    reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    final_answer = Column(String, nullable=True)

    # 부서 재배정은 master만 실행 가능(권한 체계상). staff는 "이거 우리 부서
    # 아닌 것 같다"는 요청만 남기고, master가 검토대기 큐에서 이 요청을 보고
    # 직접 재배정(/rule)하면 아래 필드들은 자동으로 초기화된다(crud.update_rule).
    dept_change_requested = Column(Boolean, default=False)
    dept_change_reason = Column(String, nullable=True)
    dept_change_suggested = Column(String, nullable=True)  # staff가 제안하는 부서(선택)
    dept_change_requested_by = Column(String, nullable=True)
    dept_change_requested_at = Column(DateTime, nullable=True)


class UserRole(str, enum.Enum):
    GENERAL = "general"
    STAFF = "staff"
    MASTER = "master"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.GENERAL, nullable=False)
    # staff 계정에만 의미 있음(role/부서 승격과 같은 방식으로 운영자가 SQL로
    # 직접 지정: UPDATE users SET department='연구원' WHERE email='...').
    # master는 전체 부서를 다 봐야 하므로 NULL로 둔다(필터링 예외 처리는
    # BE/api/inquiry.py의 list_pending_inquiries에서 role 기준으로 분기).
    department = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))