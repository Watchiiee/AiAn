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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))