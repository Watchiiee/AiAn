"""
RAG Top-3 검색 적합률(Hit@3) 평가 - 신규 평가기준 대응.

지금 최종 시스템은 동적 top_k(6~10개 반환, RAG_DYNAMIC_TOPK 기본값 True)를
쓰지만, 요구된 지표는 "Top-3 검색 문서 적합률"이므로 retrieve()가 반환한
결과 중 순위 상위 3개만 잘라서 그 안에 정답청크가 있는지를 측정한다
(Hit@3 방식 - K-5/M-2/P-3에서 이미 써온 방법론과 동일하게, classify()로
인한 노이즈를 배제하기 위해 정답 도메인을 직접 주입해 순수 검색 품질만
측정한다).

[확인 필요] retrieve()의 정확한 함수 시그니처와 RetrievedDoc.source의
정확한 포맷은 이 스크립트 작성 시점에 직접 재확인하지 못했다 - 아래
가정이 실제 코드와 다르면 import/속성 접근 부분만 빠르게 맞춰 쓰면 된다:
  - retrieve(query: str, domain: Domain) -> list[RetrievedDoc]
  - RetrievedDoc.source 형식: "파일명.md > 헤딩텍스트"
  - gold_chunk_id는 그 헤딩텍스트와 일치(M-1 참고) - source에 부분문자열로
    포함되는지로 매칭(정확히 같은 포맷이 아니어도 안전하게 매칭됨)

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_top3_retrieval
"""
import sys
import os
import csv

sys.path.insert(0, os.getcwd())

from AI.rag.retriever import retrieve  # noqa: E402
from BE.core.schemas import Domain  # noqa: E402

SOURCE_FILES = [
    "data/golden_dataset_phase1.csv",
    "data/golden_dataset_phase2.csv",
    "data/golden_dataset_bias_probe.csv",
]
TOP_N = 3


def _is_hit(gold_chunk_id: str, top3_sources: list[str]) -> bool:
    """복합질문(C유형)은 gold_chunk_id가 '+'로 여러 개 결합되어 있음(M-1) -
    그 중 하나라도 top-3 안에 있으면 hit으로 인정(관대한 기준)."""
    gold_ids = [g.strip() for g in gold_chunk_id.split("+") if g.strip()]
    for gold_id in gold_ids:
        for src in top3_sources:
            if gold_id in src:
                return True
    return False


def run():
    rows = []
    for src in SOURCE_FILES:
        if not os.path.exists(src):
            print(f"[스킵] {src} 없음")
            continue
        with open(src, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))

    total = 0
    hits = 0
    misses = []

    for row in rows:
        question = row["question"]
        gold_domain_raw = row.get("gold_domain", "").strip()
        gold_chunk_id = row.get("gold_chunk_id", "").strip()

        if not gold_domain_raw or not gold_chunk_id:
            continue

        try:
            domain = Domain(gold_domain_raw)
        except ValueError:
            print(f"[{row['id']}] gold_domain 값 이상함: {gold_domain_raw!r}, 스킵")
            continue

        total += 1

        try:
            docs = retrieve(question, domain)
        except Exception as e:
            print(f"[{row['id']}] retrieve() 실패: {e}")
            misses.append((row["id"], question, "검색실패"))
            continue

        top3_sources = [d.source for d in docs[:TOP_N]]
        hit = _is_hit(gold_chunk_id, top3_sources)

        if hit:
            hits += 1
        else:
            misses.append((row["id"], question, gold_chunk_id))

    if total == 0:
        print("평가 가능한 항목이 없습니다.")
        return

    print("=" * 70)
    print(f"RAG Top-3 검색 적합률(Hit@3) 평가 결과 (총 {total}건)")
    print("=" * 70)
    print(f"Hit@3: {hits}/{total} ({hits/total:.1%})")

    if misses:
        print(f"\n미검출 {len(misses)}건:")
        for mid, q, gold in misses:
            print(f"  [{mid}] {q[:50]} (정답: {gold})")


if __name__ == "__main__":
    run()