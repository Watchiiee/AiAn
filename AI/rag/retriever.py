"""
3단계: RAG 검색 (도메인 라우팅 버전).
질문을 임베딩해서, 지정된 도메인의 컬렉션에서 가장 비슷한 청크를 찾는다.

도메인 라우팅:
    domain="admin"     → minwon_admin      (행정·절차)
    domain="technical" → minwon_technical  (기술 질의)
1단계에서는 분류가 아직 domain 을 안 주므로 기본값 admin 으로 동작한다
(= 기존과 동일). 2단계에서 분류가 domain 을 넘겨주면 라우팅이 작동한다.

★ 사전 준비 ★ 먼저 `python -m AI.rag.ingest` 실행 필요.
"""
import chromadb

from AI.embedder import embed_text
from BE.core.schemas import RetrievedDoc, Classification

VECTOR_DIR = "data/vector_db"

DOMAIN_COLLECTIONS = {
    "admin": "minwon_admin",
    "technical": "minwon_technical",
}
DEFAULT_DOMAIN = "admin"

_client = None
_collections: dict[str, object] = {}  # 도메인별 컬렉션 캐시


def _get_collection(domain: str):
    global _client
    coll_name = DOMAIN_COLLECTIONS.get(domain, DOMAIN_COLLECTIONS[DEFAULT_DOMAIN])
    if coll_name not in _collections:
        if _client is None:
            _client = chromadb.PersistentClient(path=VECTOR_DIR)
        _collections[coll_name] = _client.get_collection(coll_name)
    return _collections[coll_name]


_NOT_READY_DOC = RetrievedDoc(
    content="(지식베이스가 아직 준비되지 않았습니다. 터미널에서 `python -m AI.rag.ingest` 를 한 번 실행하세요.)",
    source="[안내] ingest 필요",
    score=0.0,
)


def retrieve(text: str, cls: Classification, top_k: int = 3) -> list[RetrievedDoc]:
    """
    질문 text 와 의미가 가장 가까운 청크 top_k 개를 돌려준다.
    검색할 도메인은 분류 결과(cls.domain)를 따르며, 없으면 admin.

    반환:
      - 정상: 문서 리스트
      - 컬렉션 자체가 없음(ingest 안 함): [_NOT_READY_DOC]
      - 컬렉션은 있으나 결과 없음(예: technical 비어있음): [] (빈 리스트)
        → generator 에서 근거 부족(insufficient)으로 자연스럽게 처리됨
    """
    domain = getattr(cls, "domain", None) or DEFAULT_DOMAIN

    try:
        collection = _get_collection(domain)
    except Exception:
        return [_NOT_READY_DOC]

    query_vec = embed_text(text)
    res = collection.query(query_embeddings=[query_vec], n_results=top_k)

    docs: list[RetrievedDoc] = []
    documents = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        meta = meta or {}
        src = meta.get("source", "?")
        heading = meta.get("heading", "")
        source_label = f"{src} > {heading}" if heading else src
        score = 1.0 - float(dist)
        docs.append(RetrievedDoc(content=doc, source=source_label, score=round(score, 3)))

    # 빈 컬렉션(예: 아직 안 채운 technical)이면 빈 리스트 → 근거부족으로 흐름
    return docs