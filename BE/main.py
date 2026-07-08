"""
FastAPI 앱 진입점.
★ 실행은 반드시 레포 루트(AiAn/)에서 ★
    uvicorn BE.main:app --reload
문서:  http://localhost:8000/docs  (자동 생성되는 Swagger UI)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from BE.core.config import settings
from BE.api.inquiry import router as inquiry_router
from BE.api.auth import router as auth_router
from BE.db.database import init_db

app = FastAPI(title="AiAn - 전기 회사 민원 분류·답변 시스템")


@app.on_event("startup")
def on_startup():
    """서버 시작 시 필요한 테이블이 없으면 만든다."""
    init_db()

# React 개발 서버(5173/3000)에서 호출할 수 있게 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inquiry_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    """서버 상태 + API 키 연결 여부 확인용."""
    return {"status": "ok", "llm_connected": settings.has_api_key}