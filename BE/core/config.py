"""
환경설정. 레포 루트의 .env 파일에서 값을 읽어온다.
(uvicorn 을 레포 루트에서 실행하므로 .env 도 루트에 둔다)
설정값은 여기 한곳에서만 관리한다.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Gemini
    gemini_api_key: str = ""
    classifier_model: str = "gemini-2.0-flash"   # 분류: 빠르고 무료 한도 넉넉
    generator_model: str = "gemini-2.0-flash"    # 답변 생성

    use_stub_when_no_key: bool = True

    @property
    def has_api_key(self) -> bool:
        return bool(self.gemini_api_key.strip())


settings = Settings()