"""
3단계: RAG 검색.

★ 1주차 임시 버전이다. ★
지금은 ChromaDB 대신 인메모리 더미 문서에서 키워드로 대충 고른다.
목적은 '파이프라인이 끝까지 흐르는지' 확인하는 것뿐이다.

2주차 할 일:
  - data/knowledge_base/ 에 전기 회사 민원 FAQ·규정 정제 문서 채우기
  - AI/rag/ingest.py 로 청크 분리(300~500자, 약간 겹침) → 임베딩 → data/vector_db/ 에 저장
  - 이 retriever 를 ChromaDB 유사도 검색으로 교체
  - 저장/검색에 같은 임베딩 모델 사용, 청크마다 출처 메타데이터
"""
from BE.core.schemas import RetrievedDoc, InquiryType, Classification

# 유형별 더미 근거 문서 (2주차에 실제 지식베이스로 대체)
_DUMMY_KB: dict[InquiryType, list[RetrievedDoc]] = {
    InquiryType.CAREER_CERT: [
        RetrievedDoc(
            content="경력증명서는 사내 포털 '증명서 발급' 메뉴 또는 경력관리팀 방문 신청으로 발급받을 수 있습니다. 처리 기간은 영업일 기준 2~3일입니다.",
            source="[더미] 경력증명_발급절차.md",
            score=0.9,
        ),
    ],
    InquiryType.ERROR: [
        RetrievedDoc(
            content="로그인 오류 시 비밀번호 초기화 후 재시도하고, 그래도 안 되면 IT지원팀(내선 1234)으로 문의하십시오.",
            source="[더미] 로그인_장애_FAQ.md",
            score=0.85,
        ),
    ],
}

_DEFAULT_DOC = RetrievedDoc(
    content="해당 문의에 대한 안내 자료를 준비 중입니다. 담당 부서에서 확인 후 회신드립니다.",
    source="[더미] 기본안내.md",
    score=0.3,
)


def retrieve(text: str, cls: Classification, top_k: int = 3) -> list[RetrievedDoc]:
    docs = _DUMMY_KB.get(cls.type, [])
    if not docs:
        docs = [_DEFAULT_DOC]
    return docs[:top_k]