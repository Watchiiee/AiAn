"""
retrieve()의 RRF 융합 과정을 그대로 재현해서, 벡터 순위·BM25 순위·최종 융합점수를
전부 단계별로 보여주는 진단 스크립트. "정답청크가 왜 최종 top-k 밖으로 밀렸는지"를
정확히 짚기 위함(BM25 자체는 정상임이 debug_bm25_only.py로 이미 확인됨).

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_fusion
    python3 -m scripts.debug_fusion "다른 질문" technical
"""
import sys
import os

sys.path.insert(0, os.getcwd())

from AI.embedder import embed_text  # noqa: E402
from AI.rag import bm25_index  # noqa: E402
from AI.rag.retriever import _get_collection, DOMAIN_COLLECTIONS, FUSION_POOL, RRF_K  # noqa: E402

DEFAULT_QUESTION = "IEEE Std 142 기준으로 공통접지 접지저항은 몇 옴이어야 하나요?"
DEFAULT_DOMAIN = "technical"
GOLD_HEADING_KEYWORD = "공통접지"


def run(question: str, domain: str):
    coll_name = DOMAIN_COLLECTIONS[domain]
    collection = _get_collection(domain)

    print(f"질문: {question}")
    print(f"FUSION_POOL={FUSION_POOL}, RRF_K={RRF_K}\n")

    # 1) 벡터 검색 (FUSION_POOL개)
    query_vec = embed_text(question)
    res = collection.query(query_embeddings=[query_vec], n_results=FUSION_POOL)
    vec_ids = res.get("ids", [[]])[0]
    vec_metas = res.get("metadatas", [[]])[0]
    vec_dists = res.get("distances", [[]])[0]

    print(f"--- 벡터 검색 결과 (top {len(vec_ids)}) ---")
    gold_vec_rank = None
    for i, (doc_id, meta, dist) in enumerate(zip(vec_ids, vec_metas, vec_dists), 1):
        heading = (meta or {}).get("heading", "")
        cosine = round(1.0 - float(dist), 3)
        marker = ""
        if GOLD_HEADING_KEYWORD in heading:
            marker = "  <-- 정답청크"
            gold_vec_rank = i
        print(f"  {i:>2}위 (cosine={cosine}) {heading[:45]}{marker}")
    print(f"  => 정답청크의 벡터 순위: {gold_vec_rank if gold_vec_rank else '벡터 top-' + str(FUSION_POOL) + ' 밖 (전혀 없음)'}\n")

    # 2) BM25 검색 (FUSION_POOL개)
    bm25_results = bm25_index.search(question, coll_name, top_k=FUSION_POOL)
    print(f"--- BM25 검색 결과 (top {len(bm25_results)}) ---")
    gold_bm25_rank = None
    bm25_headings = {}
    for i, (doc_id, score) in enumerate(bm25_results, 1):
        fetched = bm25_index.get_doc(coll_name, doc_id)
        heading = fetched[1].get("heading", "") if fetched else ""
        bm25_headings[doc_id] = heading
        marker = ""
        if GOLD_HEADING_KEYWORD in heading:
            marker = "  <-- 정답청크"
            gold_bm25_rank = i
        print(f"  {i:>2}위 (bm25={score:.2f}) {heading[:45]}{marker}")
    print(f"  => 정답청크의 BM25 순위: {gold_bm25_rank}\n")

    # 3) RRF 융합 재현
    vec_rank = {doc_id: i + 1 for i, doc_id in enumerate(vec_ids)}
    bm25_rank = {doc_id: i + 1 for i, (doc_id, _) in enumerate(bm25_results)}
    all_ids = set(vec_rank) | set(bm25_rank)

    rrf_scores = {}
    for doc_id in all_ids:
        s = 0.0
        if doc_id in vec_rank:
            s += 1.0 / (RRF_K + vec_rank[doc_id])
        if doc_id in bm25_rank:
            s += 1.0 / (RRF_K + bm25_rank[doc_id])
        rrf_scores[doc_id] = s

    ranked = sorted(all_ids, key=lambda d: rrf_scores[d], reverse=True)

    print("--- RRF 최종 융합 순위 (전체) ---")
    gold_final_rank = None
    for i, doc_id in enumerate(ranked, 1):
        vr = vec_rank.get(doc_id, "-")
        br = bm25_rank.get(doc_id, "-")
        # 헤딩 조회 (벡터쪽 메타 or bm25쪽 메타)
        heading = ""
        if doc_id in vec_ids:
            idx = vec_ids.index(doc_id)
            heading = (vec_metas[idx] or {}).get("heading", "")
        else:
            heading = bm25_headings.get(doc_id, "")
        marker = ""
        if GOLD_HEADING_KEYWORD in heading:
            marker = "  <-- 정답청크"
            gold_final_rank = i
        print(f"  {i:>2}위 (rrf={rrf_scores[doc_id]:.5f}, 벡터순위={vr}, bm25순위={br}) {heading[:40]}{marker}")

    print(f"\n=> 정답청크의 최종 융합 순위: {gold_final_rank}")
    print("\n해석: 정답청크보다 위에 있는 문서들이 '벡터·BM25 둘 다에서 중간 순위'를 받아 점수가")
    print("      누적된 경우라면, 지금 RRF 공식(양쪽 동일 가중치)이 강력한 단일신호(BM25 1위처럼")
    print("      압도적 격차)보다 '양쪽에 걸치는 것'을 더 우대하고 있다는 뜻 — RRF_K 조정이나")
    print("      가중치 비대칭화가 필요할 수 있음.")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    d = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DOMAIN
    run(q, d)