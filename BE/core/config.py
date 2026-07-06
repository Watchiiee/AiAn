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

    # --- (보존) 이전 사용: Google Gemini ---
    #   되돌리려면 아래 주석 해제 + has_api_key 를 gemini_api_key 기준으로 교체
    # gemini_api_key: str = ""
    # classifier_model: str = "gemini-2.5-flash-lite"
    # generator_model: str = "gemini-2.5-flash-lite"

    use_stub_when_no_key: bool = True

    @property
    def has_api_key(self) -> bool:
        return bool(self.clova_api_key.strip())
        # (Gemini 시절) return bool(self.gemini_api_key.strip())


settings = Settings()