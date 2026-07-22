# --- 베이스 이미지 ---
FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary는 미리 컴파일된 배포판이라 build-essential/libpq-dev(컴파일용 도구)가
# 필요 없음 - 그래서 이미지를 가볍게 유지하려고 굳이 안 넣음.
# curl은 헬스체크(HEALTHCHECK)에서 쓰려고 남겨둠.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# --- 파이썬 의존성 ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 임베딩 모델 미리 다운로드 (컨테이너 시작마다 다시 받지 않도록 빌드 시점에 캐싱) ---
# ko-sroberta-multitask(442MB)를 여기서 미리 받아두면 콜드스타트가 빨라지고,
# 실행 중 HuggingFace Hub 요청(그동안 로그에 뜨던 "unauthenticated requests" 경고)도 줄어듦
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"

# --- 앱 코드 복사 ---
COPY AI/ ./AI/
COPY BE/ ./BE/
COPY data/knowledge_base/ ./data/knowledge_base/
# data/vector_db는 복사하지 않음 - 아래에서 이 시점에 새로 생성(ingest)함
# (지식베이스 markdown이 이미지에 포함되므로, 벡터DB도 빌드 시점에 미리 만들어두면
#  컨테이너가 뜰 때마다 임베딩을 다시 계산할 필요가 없음)
RUN python -m AI.rag.ingest

# --- 실행 ---
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1
# --reload는 개발용 옵션이므로 프로덕션 이미지에는 넣지 않음
CMD ["uvicorn", "BE.main:app", "--host", "0.0.0.0", "--port", "8000"]