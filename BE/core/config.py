"""
환경설정. 레포 루트의 .env 파일에서 값을 읽어온다.
(uvicorn 을 레포 루트에서 실행하므로 .env 도 루트에 둔다)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- 현재 사용: CLOVA Studio (HyperCLOVA X) ---
    clova_api_key: str = ""
    classifier_model: str = "HCX-005"   # 분류
    generator_model: str = "HCX-005"    # 답변 생성

    use_stub_when_no_key: bool = True

    # RAG 근거 판정: 검색 최고 score가 이 값 미만이면 '명백히 근거 없음'으로 보고
    # LLM을 부르지 않고 바로 insufficient 처리한다. (실측: 관련 0.6~0.7 / 무관 0.3)
    no_evidence_threshold: float = 0.4

    # --- 데이터베이스 (문의 이력 저장) ---
    database_url: str = "postgresql+psycopg2://localhost:5432/aian"

    # JWT 인증
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- Langfuse (LangGraph 파이프라인 관측/트레이싱) ---
    # 비워두면 트레이싱 없이 그냥 동작한다 (관측은 부가 기능, 필수 아님)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def has_api_key(self) -> bool:
        return bool(self.clova_api_key.strip())


settings = Settings()