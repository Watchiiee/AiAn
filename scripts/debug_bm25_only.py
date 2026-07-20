"""
BM25만 단독으로(RRF 융합 없이) 검색해서 결과를 확인하는 진단 스크립트.
RRF 융합 로직을 완전히 배제한 상태에서 "BM25 인덱싱·토큰화 자체가 정상인지"만
격리해서 본다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_bm25_only
    python3 -m scripts.debug_bm25_only "다른 질문" technical
"""
import sys
import os

sys.path.insert(0, os.getcwd())

from AI.rag import bm25_index  # noqa: E402

DOMAIN_COLLECTIONS = {
    "admin": "minwon_admin",
    "technical": "minwon_technical",
}

DEFAULT_QUESTION = "IEEE Std 142 기준으로 공통접지 접지저항은 몇 옴이어야 하나요?"
DEFAULT_DOMAIN = "technical"
GOLD_HEADING_KEYWORD = "공통접지"  # G05 정답청크의 헤딩에 포함된 키워드로 식별


def run(question: str, domain: str):
    coll_name = DOMAIN_COLLECTIONS[domain]
    print(f"질문: {question}")
    print(f"토큰화 결과: {bm25_index.tokenize(question)}")
    print(f"검색 대상 컬렉션: {coll_name}\n")

    results = bm25_index.search(question, coll_name, top_k=20)

    if not results:
        print("⚠️ BM25 결과가 0개 — 토큰화된 질의어가 코퍼스의 어떤 문서와도 겹치지 않는다는 뜻.")
        print("   (BM25는 코사인 유사도처럼 '조금이라도 비슷하면' 걸리는 게 아니라, 토큰이 하나라도")
        print("    겹쳐야 점수가 생긴다 — 완전히 0개면 인덱싱 자체보다 토큰 불일치를 의심해야 함)")
        return

    print(f"BM25 결과 {len(results)}개:\n")
    gold_rank = None
    for i, (doc_id, score) in enumerate(results, 1):
        fetched = bm25_index.get_doc(coll_name, doc_id)
        if fetched:
            content, meta = fetched
            source = meta.get("source", "?")
            heading = meta.get("heading", "")
        else:
            source, heading = "(조회실패)", ""

        marker = ""
        if GOLD_HEADING_KEYWORD in heading:
            marker = "  <-- 정답청크로 추정"
            gold_rank = i

        print(f"{i:>2}위 | bm25점수={score:.3f} | {source} > {heading[:50]}{marker}")

    print()
    if gold_rank:
        print(f"결론: 정답청크가 BM25 단독 결과에서 {gold_rank}위 — BM25 인덱싱/토큰화는 정상.")
        print("      문제는 RRF 융합 단계(가중치·top-N 제한)에 있을 가능성이 높음.")
    else:
        print("결론: 정답청크가 BM25 결과 20위 안에 전혀 없음 — BM25 인덱싱 또는 토큰화 자체에 문제.")


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    d = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DOMAIN
    run(q, d)