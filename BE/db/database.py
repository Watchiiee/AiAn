"""
데이터베이스 연결 설정.
DATABASE_URL 은 .env 에서 읽는다 — 로컬은 Postgres.app,
배포 시엔 이 값만 클라우드 DB 주소로 바꾸면 된다 (코드는 그대로).

사용법 (다른 모듈에서):
    from BE.db.database import get_db
    def some_endpoint(db: Session = Depends(get_db)):
        ...
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from BE.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 의존성 주입용. 요청마다 세션을 열고 끝나면 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """테이블이 없으면 생성한다. 서버 시작 시 한 번 호출."""
    from BE.db import models  # noqa: F401  (모델 등록을 위해 import)
    Base.metadata.create_all(bind=engine)