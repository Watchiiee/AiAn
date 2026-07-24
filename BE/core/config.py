"""
환경설정. 레포 루트의 .env 파일에서 값을 읽어온다.
(uvicorn 을 레포 루트에서 실행하므로 .env 도 루트에 둔다)
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # CORS 허용 origin — 쉼표로 구분해서 .env에 설정(예: 배포 시 실제 프론트
    # 도메인/IP 추가). 기본값은 로컬 개발(Vite dev server, 5173/3000)만 허용
    # — 이 값들이 있어야 로컬 개발이 그대로 동작하므로, 배포 주소는 여기에
    # "추가"하는 형태로 쓸 것(덮어쓰지 말고 이어붙이기).
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    # --- 현재 사용: CLOVA Studio (HyperCLOVA X) ---
    clova_api_key: str = ""
    classifier_model: str = "HCX-005"   # 분류
    generator_model: str = "HCX-005"    # 답변 생성

    use_stub_when_no_key: bool = True

    # --- Upstage Solar (hallucination_grade 전용, 실험적) ---
    # 목적: doc_grade(근거를 고르는 모델)와 hallucination_grade(그 근거로 만든
    # 답을 검증하는 모델)가 같으면, 그 모델 고유의 편향을 이중검증 단계에서도
    # 똑같이 놓칠 수 있다는 우려 때문에 검증 게이트만 별도 모델로 시험해본다.
    # doc_grade/classify_domain은 이번 세션에 막 안정화됐으므로 손대지 않고
    # 유지한다(DECISION_LOG 참고). 개선이 확인되면 answer_grade도 같은 방식으로
    # 검토할 예정 — 한 번에 하나씩만 바꾸는 원칙.
    # 기본값은 clova(기존 동작과 100% 동일). Solar로 바꾼 뒤에는 반드시 골든셋으로
    # false negative/positive 비율을 CLOVA 단독과 비교하고 나서 기본값 전환을 판단할 것.
    upstage_api_key: str = ""
    hallucination_grader_provider: str = "clova"   # "clova" 또는 "upstage"
    hallucination_grader_model: str = "HCX-005"     # upstage일 때는 실제 Solar

    # --- 담당자 코파일럿(StaffPage 사이드바 대화형 도우미) ---
    # 스트리밍(call_llm_stream)이 CLOVA 실측(scripts/debug_clova_stream.py)으로
    # event:token/result/signal 구조까지 검증됐으므로 기본값은 clova.
    # hallucination_grader와 같은 패턴 - 다른 provider로 시험 전환 가능.
    copilot_provider: str = "clova"
    copilot_model: str = "HCX-005"

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

    # --- Ops 모니터링 리포트 이메일 발송 (SMTP) ---
    # 새 이메일 서비스 연동을 추가하지 않고, 표준 SMTP(Gmail 앱비밀번호 등으로
    # 바로 가능)로 간단하게 처리한다. 이 값들이 없으면 발송을 건너뛰고 콘솔에
    # 리포트만 출력(scripts/run_ops_monitor.py 참고) - 이메일 설정이 안 됐다고
    # 리포트 생성 자체가 실패하면 안 되므로.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    ops_report_recipient: str = ""

    @property
    def has_api_key(self) -> bool:
        return bool(self.clova_api_key.strip())


settings = Settings()

print(f"[config.py 설정] hallucination_grader_provider={settings.hallucination_grader_provider}, "
      f"hallucination_grader_model={settings.hallucination_grader_model}, "
      f"copilot_provider={settings.copilot_provider}, copilot_model={settings.copilot_model}, "
      f"upstage_api_key_set={bool(settings.upstage_api_key.strip())}")