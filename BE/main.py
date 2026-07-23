from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from BE.core.config import settings
from BE.api.inquiry import router as inquiry_router
from BE.api.auth import router as auth_router
from BE.db.database import init_db

app = FastAPI(title="AiAn - 전기 회사 민원 분류·답변 시스템")


@app.on_event("startup")
def on_startup():
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inquiry_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok", "llm_connected": settings.has_api_key}

#