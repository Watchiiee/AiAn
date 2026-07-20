"""
3단계: RAG 검색 (도메인 라우팅 + 벡터·BM25 하이브리드 RRF 융합 버전).

하이브리드 검색을 넣은 이유: harmonics(표), TN-S(약어), IEEE Std 142(표준명) 3건
모두 "정답은 있는데 임베딩 검색 순위가 밀리는" 문제였고, 이런 영문 약어·표준명·
숫자단위는 BM25(정확한 키워드 매칭)가 구조적으로 강하다. 벡터 검색(의미 유사도)과
BM25(키워드 정확매칭)를 RRF(Reciprocal Rank Fusion)로 합쳐서, 어느 한쪽이 놓친
것을 다른 쪽이 구제하게 한다.
"""
import os
import chromadb

from AI.embedder import embed_text
from AI.rag import bm25_index
from BE.core.schemas import RetrievedDoc, Classification

VECTOR_DIR = "data/vector_db"

DOMAIN_COLLECTIONS = {
    "admin": "minwon_admin",
    "technical": "minwon_technical",
}
DEFAULT_DOMAIN = "admin"

FUSION_POOL = 20
RRF_K = 60

# 비교실험용 스위치: RAG_USE_HYBRID=1로 실행하면 BM25+RRF 하이브리드를 사용.
# 기본값은 0(벡터전용) — 89개 골든셋 실측 결과 하이브리드가 recall 97.2%→94.4%,
# Precision@1 80.9%→73.0%로 전반적 순손실이었고, 하이브리드를 만든 원래 목적
# (G05: IEEE Std 142)조차 벡터전용에서 이미 1위로 해결되고 있어 실익이 없었음
# (DECISION_LOG 참고). RRF가 "양쪽에서 어중간한 문서"를 "한쪽에서 확실한 1위"
# 보다 우대하는 부작용이 넓게 발생한 것으로 진단됨 — 균등가중 RRF를 그대로 켜는
# 것은 위험하므로 기본은 끔. 추후 신호강도 기반 임계값 등으로 개선 후 재검토.
USE_HYBRID = os.environ.get("RAG_USE_HYBRID", "0") == "1"

_client = None
_collections: dict[str, object] = {}


def _get_collection(domain: str):
    global _client
    coll_name = DOMAIN_COLLECTIONS.get(domain, DOMAIN_COLLECTIONS[DEFAULT_DOMAIN])
    if coll_name not in _collections:
        if _client is None:
            _client = chromadb.PersistentClient(path=VECTOR_DIR)
        _collections[coll_name] = _client.get_collection(coll_name)
    return _collections[coll_name]


def _source_label(meta: dict) -> str:
    meta = meta or {}
    src = meta.get("source", "?")
    heading = meta.get("heading", "")
    return f"{src} > {heading}" if heading else src


_NOT_READY_DOC = RetrievedDoc(
    content="(지식베이스가 아직 준비되지 않았습니다. 터미널에서 `python -m AI.rag.ingest` 를 한 번 실행하세요.)",
    source="[안내] ingest 필요",
    score=0.0,
)


def retrieve(text: str, cls: Classification, top_k: int = 3) -> list[RetrievedDoc]:
    domain = getattr(cls, "domain", None)
    domain = domain.value if hasattr(domain, "value") else (domain or DEFAULT_DOMAIN)
    coll_name = DOMAIN_COLLECTIONS.get(domain, DOMAIN_COLLECTIONS[DEFAULT_DOMAIN])

    try:
        collection = _get_collection(domain)
    except Exception:
        return [_NOT_READY_DOC]

    query_vec = embed_text(text)

    # --- 벡터전용 경로 (RAG_USE_HYBRID=0일 때, 하이브리드 도입 전과 동일한 동작) ---
    if not USE_HYBRID:
        res = collection.query(query_embeddings=[query_vec], n_results=top_k)
        documents = res.get("documents", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        distances = res.get("distances", [[]])[0]
        docs: list[RetrievedDoc] = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            score = round(1.0 - float(dist), 3)
            docs.append(RetrievedDoc(content=doc, source=_source_label(meta), score=score, rrf_score=None))
        return docs if docs else [_NOT_READY_DOC]

    # --- 하이브리드 경로 (벡터 + BM25 RRF 융합) ---
    # 1) 벡터 검색 (넉넉히 FUSION_POOL개)
    res = collection.query(query_embeddings=[query_vec], n_results=FUSION_POOL)
    vec_ids = res.get("ids", [[]])[0]
    vec_docs = res.get("documents", [[]])[0]
    vec_metas = res.get("metadatas", [[]])[0]
    vec_dists = res.get("distances", [[]])[0]

    cosine_by_id: dict[str, float] = {}
    doc_by_id: dict[str, tuple[str, dict]] = {}
    for doc_id, doc, meta, dist in zip(vec_ids, vec_docs, vec_metas, vec_dists):
        cosine_by_id[doc_id] = round(1.0 - float(dist), 3)
        doc_by_id[doc_id] = (doc, meta or {})

    # 2) BM25 검색 (넉넉히 FUSION_POOL개). 실패해도(예: 인덱스 구축 오류) 벡터 검색
    #    결과만으로 계속 진행할 수 있어야 하므로 방어적으로 처리.
    try:
        bm25_results = bm25_index.search(text, coll_name, top_k=FUSION_POOL)
    except Exception:
        bm25_results = []

    for doc_id, _bm25_score in bm25_results:
        if doc_id not in doc_by_id:
            fetched = bm25_index.get_doc(coll_name, doc_id)
            if fetched:
                doc_by_id[doc_id] = fetched

    # 3) RRF 융합: 각 방법에서의 등수(1위부터)를 기준으로 1/(RRF_K+등수)를 더함.
    #    한쪽에만 있으면 그 항만 더해짐(다른 쪽은 0으로 취급).
    vec_rank = {doc_id: i + 1 for i, doc_id in enumerate(vec_ids)}
    bm25_rank = {doc_id: i + 1 for i, (doc_id, _) in enumerate(bm25_results)}

    all_ids = set(vec_rank) | set(bm25_rank)
    rrf_scores: dict[str, float] = {}
    for doc_id in all_ids:
        s = 0.0
        if doc_id in vec_rank:
            s += 1.0 / (RRF_K + vec_rank[doc_id])
        if doc_id in bm25_rank:
            s += 1.0 / (RRF_K + bm25_rank[doc_id])
        rrf_scores[doc_id] = s

    ranked_ids = sorted(all_ids, key=lambda d: rrf_scores[d], reverse=True)[:top_k]

    docs: list[RetrievedDoc] = []
    for doc_id in ranked_ids:
        content, meta = doc_by_id[doc_id]
        docs.append(RetrievedDoc(
            content=content,
            source=_source_label(meta),
            score=cosine_by_id.get(doc_id, 0.0),  # BM25로만 찾은 문서는 코사인값이 없어 0.0
            rrf_score=round(rrf_scores[doc_id], 5),
        ))

    return docs if docs else [_NOT_READY_DOC]