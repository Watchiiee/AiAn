"""
환경설정. 레포 루트의 .env 파일에서 값을 읽어온다.
(uvicorn 을 레포 루트에서 실행하므로 .env 도 루트에 둔다)
설정값은 여기 한곳에서만 관리한다.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    classifier_model: str = "claude-haiku-4-5-20251001"
    generator_model: str = "claude-sonnet-4-6"
    use_stub_when_no_key: bool = True

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key.strip())


settings = Settings()