"""
pytest 공통 픽스처.

chromadb/rank_bm25/sentence_transformers는 실제 서버 실행 때만 필요한
무거운 의존성이라(모델 다운로드 등), 테스트에서는 스텁으로 대체한다 -
이 프로젝트 대부분의 디버그 스크립트(scripts/debug_*.py)에서 검증에
써온 것과 동일한 방식이다. conftest.py는 다른 테스트 파일들이 import되기
전에 가장 먼저 실행되므로, 여기서 스텁을 걸어두면 이후 모든 테스트에
안전하게 적용된다.
"""
import sys
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


class _Stub:
    def __init__(self, *a, **k):
        pass


for _mod_name in ["chromadb", "rank_bm25", "sentence_transformers"]:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = type(sys)(_mod_name)

sys.modules["chromadb"].PersistentClient = _Stub
sys.modules["rank_bm25"].BM25Okapi = _Stub
sys.modules["sentence_transformers"].SentenceTransformer = _Stub

import pytest  # noqa: E402


@pytest.fixture
def db_session():
    """테스트마다 완전히 새로운 in-memory SQLite DB를 만들어 준다 - 테스트 간
    데이터가 서로 섞이지 않게 함."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from BE.db.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_inquiry(db_session):
    """테스트용 InquiryRecord를 손쉽게 만드는 헬퍼. 필요한 필드만 넘기고
    나머지는 합리적인 기본값으로 채운다."""
    from BE.db.models import InquiryRecord

    def _make(**overrides):
        defaults = dict(
            user_id=1,
            original_text="테스트 문의",
            inquiry_type="일반문의",
            domain="technical",
            confidence=0.9,
            department="연구원",
            priority="보통",
            answer_draft="테스트 답변",
            answer_confidence="sufficient",
            used_llm=True,
            retrieved_docs=[],
        )
        defaults.update(overrides)
        record = InquiryRecord(**defaults)
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record

    return _make