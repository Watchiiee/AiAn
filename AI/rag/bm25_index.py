"""
BM25 키워드 검색 인덱스.

목적: 영문 약어·표준명·숫자+단위(TN-S, IEEE Std 142, 154kV 등)가 임베딩
검색에서 종종 누락되는 문제(harmonics 표, TN-S, IEEE Std 142 — 3건 실증)를
보완하기 위한 키워드 매칭 축. 벡터 검색과 RRF로 융합해서 쓴다(retriever.py).

설계 원칙:
- 청크 수가 지금 규모(수백 개)에서는 서버 시작 시 메모리에 즉석 생성하는 것으로
  충분하다. 디스크 캐싱은 하지 않음 — ChromaDB 문서가 바뀌었는데 BM25 인덱스가
  갱신 안 되는 동기화 버그를 원천 차단하기 위함. [메모] 청크 수가 수만 개
  단위로 늘어나면 이 방식(매 재시작마다 전체 재인덱싱)은 재검토가 필요하다.
- 토큰화는 형태소분석기를 쓰지 않고 정규식만 사용한다. BM25를 쓰는 목적이
  한국어 조사/어미 처리가 아니라 "영문 약어·표준명·숫자단위의 정확한 매칭"이므로,
  형태소분석기가 오히려 "IEEE Std 142" 같은 토큰을 잘못 쪼갤 위험이 있어 목적에
  맞지 않는다.
"""
import re
import chromadb
from rank_bm25 import BM25Okapi

VECTOR_DIR = "data/vector_db"

# 토큰화 규칙: ① 영문 연속(대소문자 무관) ② 숫자(소수점 포함, 예: 22.9) ③ 한글 어절.
# 하이픈(-)은 별도 토큰으로 캡처하지 않고 구분자로만 취급한다 — "TN-S"와 "TN S",
# "IEEE-80"과 "IEEE 80"처럼 표기가 미세하게 다른 경우에도 동일하게 토큰화되어
# 매칭이 깨지지 않도록 하기 위함(대신 "TN-S"가 "tn"+"s" 두 토큰으로 쪼개지지만,
# BM25는 문서·질의 양쪽에 동일하게 적용되므로 매칭 자체에는 문제가 없다).
_TOKEN_RE = re.compile(r"[A-Za-z]+|[0-9]+(?:\.[0-9]+)?|[가-힣]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


_client = None
_index_cache: dict[str, dict] = {}  # coll_name -> {"bm25", "ids", "docs", "metas"}


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=VECTOR_DIR)
    return _client


def _build_index(coll_name: str):
    client = _get_client()
    collection = client.get_collection(coll_name)
    data = collection.get(include=["documents", "metadatas"])
    ids = data["ids"]
    docs = data["documents"]
    metas = data["metadatas"]
    tokenized_corpus = [tokenize(d) for d in docs]
    bm25 = BM25Okapi(tokenized_corpus)
    _index_cache[coll_name] = {"bm25": bm25, "ids": ids, "docs": docs, "metas": metas}


def search(text: str, coll_name: str, top_k: int = 20) -> list[tuple[str, float]]:
    """
    coll_name(ChromaDB 컬렉션명) 안에서 BM25로 검색해 (doc_id, bm25_score)를
    점수 내림차순으로 top_k개 반환. 인덱스가 없으면 즉석 생성한다.
    """
    if coll_name not in _index_cache:
        _build_index(coll_name)
    idx = _index_cache[coll_name]
    if not idx["ids"]:
        return []
    scores = idx["bm25"].get_scores(tokenize(text))
    ranked = sorted(zip(idx["ids"], scores), key=lambda x: x[1], reverse=True)
    return [(doc_id, score) for doc_id, score in ranked[:top_k] if score > 0]


def get_doc(coll_name: str, doc_id: str):
    """doc_id로 (content, metadata) 조회. 벡터검색엔 없고 BM25에만 걸린 문서를 채우는 용도."""
    idx = _index_cache.get(coll_name)
    if not idx:
        return None
    try:
        i = idx["ids"].index(doc_id)
    except ValueError:
        return None
    return idx["docs"][i], idx["metas"][i]