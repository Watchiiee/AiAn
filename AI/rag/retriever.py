"""
3단계: RAG 검색 (진짜 ChromaDB 버전).
질문을 임베딩해서 ChromaDB에서 가장 비슷한 청크를 찾는다.

★ 사전 준비 ★ 먼저 `python -m AI.rag.ingest` 를 한 번 실행해
   data/vector_db/ 에 벡터를 만들어 둬야 한다.
   (아직 안 했으면 아래 폴백 안내 문구가 대신 나온다.)
"""
import chromadb
from chromadb.errors import ChromaError

from AI.embedder import embed_text
from BE.core.schemas import RetrievedDoc, Classification

VECTOR_DIR = "data/vector_db"
COLLECTION_NAME = "minwon_kb"

_collection = None  # 한 번만 연결


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=VECTOR_DIR)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


# 아직 ingest 안 한 경우 보여줄 안내
_NOT_READY_DOC = RetrievedDoc(
    content="(지식베이스가 아직 준비되지 않았습니다. 터미널에서 `python -m AI.rag.ingest` 를 한 번 실행하세요.)",
    source="[안내] ingest 필요",
    score=0.0,
)


def retrieve(text: str, cls: Classification, top_k: int = 3) -> list[RetrievedDoc]:
    """질문 text 와 의미가 가장 가까운 청크 top_k 개를 돌려준다."""
    try:
        collection = _get_collection()
    except Exception:
        # 컬렉션이 없음 = 아직 ingest 안 함
        return [_NOT_READY_DOC]

    query_vec = embed_text(text)
    res = collection.query(query_embeddings=[query_vec], n_results=top_k)

    docs: list[RetrievedDoc] = []
    documents = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    distances = res.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        meta = meta or {}
        # 출처 = 파일명 + 제목 (답변 근거 표시 + 평가 점수용)
        src = meta.get("source", "?")
        heading = meta.get("heading", "")
        source_label = f"{src} > {heading}" if heading else src
        # cosine distance(0~2) → 유사도 점수(1~-1)로 환산
        score = 1.0 - float(dist)
        docs.append(RetrievedDoc(content=doc, source=source_label, score=round(score, 3)))

    return docs or [_NOT_READY_DOC]