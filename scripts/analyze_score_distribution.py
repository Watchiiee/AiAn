"""
엘보우(점수 격차) 임계값 실험용 스크립트.

골든셋 각 질문에 대해 top-10 검색 점수를 그대로 뽑아, 등수 간 점수 격차(gap)를
계산한다. 목적은 "몇 등과 몇 등 사이에서 점수가 뚝 떨어지는 절벽(elbow)이
생기는지"를 실제 데이터로 확인하는 것 — L-3에서 보류했던 "동적 top_k(엘보우 방식)"
임계값을 매직넘버로 정하지 않고 데이터 기반으로 산출하기 위한 사전 조사용.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.analyze_score_distribution
    python3 -m scripts.analyze_score_distribution data/golden_dataset_phase1.csv

결과: 콘솔에 질문별 점수 목록 + 최대 격차 위치 출력, 그리고 "정답청크 등수 대비
최대격차 위치"를 비교해 엘보우가 실제로 정답 근처에서 생기는지 보여줌.
data/test_results/score_distribution_<시각>.csv 로도 저장(등수별 원점수 전부 포함,
나중에 스프레드시트로 직접 그려볼 수 있게).
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.getcwd())

from AI.rag.retriever import retrieve  # noqa: E402
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory  # noqa: E402

DEFAULT_CSVS = ["data/golden_dataset_phase1.csv", "data/golden_dataset_phase2.csv"]
TOP_K = 10


def load_golden_set(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def _parse_gold_chunks(gold_chunk_id: str) -> list[tuple[str, str]]:
    parts = [p.strip() for p in gold_chunk_id.split(" + ")]
    result = []
    for p in parts:
        segs = [s.strip() for s in p.split(">")]
        result.append((segs[0], segs[-1]))
    return result


def _parse_retrieved_source(source: str) -> tuple[str, str]:
    if " > " in source:
        filename, heading = source.split(" > ", 1)
        return filename.strip(), heading.strip()
    return source.strip(), ""


def _dummy_classification(domain: str) -> Classification:
    return Classification(
        type=InquiryType.GENERAL, key_request="score dist 분석용", confidence=1.0,
        domain=Domain(domain), category=BusinessCategory.OTHER, is_relevant=True,
    )


def run(csv_paths: list[str]):
    rows = load_golden_set(csv_paths)
    print(f"{len(rows)}개 질문 분석 중...\n")

    csv_rows = []
    gold_rank_vs_max_gap_rank = []  # (정답 등수, 최대격차 발생 위치) 쌍 모음

    for r in rows:
        cls = _dummy_classification(r["gold_domain"])
        docs = retrieve(r["question"], cls, top_k=TOP_K)
        scores = [d.score for d in docs]

        gold_pairs = _parse_gold_chunks(r["gold_chunk_id"])
        retrieved_pairs = [_parse_retrieved_source(d.source) for d in docs]
        gold_rank = None
        for i, rp in enumerate(retrieved_pairs, 1):
            if rp in gold_pairs:
                gold_rank = i
                break

        # 등수 i와 i+1 사이 점수 격차 계산
        gaps = [scores[i] - scores[i + 1] for i in range(len(scores) - 1)]
        max_gap_idx = gaps.index(max(gaps)) + 1 if gaps else None  # 1-indexed: "몇 등 뒤에서 격차가 가장 큰지"

        scores_str = ", ".join(f"{s:.3f}" for s in scores)
        print(f"[{r['id']}] 정답등수={gold_rank} | 최대격차위치={max_gap_idx}등 뒤 | 점수: {scores_str}")

        csv_rows.append({
            "id": r["id"], "question": r["question"], "gold_rank": gold_rank,
            "max_gap_after_rank": max_gap_idx,
            **{f"score_{i+1}": (scores[i] if i < len(scores) else "") for i in range(TOP_K)},
        })

        if gold_rank is not None and max_gap_idx is not None:
            gold_rank_vs_max_gap_rank.append((gold_rank, max_gap_idx))

    # --- 엘보우가 정답 등수 근처에서 실제로 생기는지 집계 ---
    print("\n" + "=" * 70)
    print("엘보우(최대격차) 위치가 정답 등수와 얼마나 가까운지")
    print("=" * 70)
    exact_match = sum(1 for g, m in gold_rank_vs_max_gap_rank if m == g)
    within_1 = sum(1 for g, m in gold_rank_vs_max_gap_rank if abs(m - g) <= 1)
    after_gold = sum(1 for g, m in gold_rank_vs_max_gap_rank if m >= g)
    total = len(gold_rank_vs_max_gap_rank)
    print(f"정답청크가 검색된 문항: {total}개")
    print(f"  최대격차 위치 == 정답등수: {exact_match}개 ({exact_match/total:.1%})")
    print(f"  최대격차 위치가 정답등수 ±1 이내: {within_1}개 ({within_1/total:.1%})")
    print(f"  최대격차 위치가 정답등수 이후(정답을 자르지 않음): {after_gold}개 ({after_gold/total:.1%})")
    print("\n해석: '정답등수 이후' 비율이 높으면 엘보우 컷이 정답을 안전하게 포함한다는 뜻.")
    print("      낮으면(정답 이전에 컷) 엘보우 방식이 오히려 정답을 잘라낼 위험이 있다는 뜻.")

    # --- [신규] 실패 사례(엘보우가 정답보다 먼저 끊는 경우) 목록 + min_k 권장값 ---
    failures = [(g, m) for g, m in gold_rank_vs_max_gap_rank if m < g]
    print("\n" + "=" * 70)
    print(f"실패 사례 (엘보우가 정답 등수 이전에 끊어버리는 경우): {len(failures)}개")
    print("=" * 70)
    if failures:
        for r in csv_rows:
            if r["gold_rank"] is not None and r["max_gap_after_rank"] is not None and r["max_gap_after_rank"] < r["gold_rank"]:
                print(f"  [{r['id']}] 정답등수={r['gold_rank']}, 엘보우위치={r['max_gap_after_rank']} | {r['question'][:40]}")
        fail_gold_ranks = [g for g, m in failures]
        suggested_min_k = max(fail_gold_ranks)
        print(f"\n실패 사례들의 정답등수: {sorted(fail_gold_ranks)}")
        print(f"=> min_k를 {suggested_min_k}로 설정하면 이번 실패 사례 전부가 커버됨")
        print(f"   (엘보우가 그보다 일찍 끊으려 해도 최소 {suggested_min_k}개까지는 무조건 보게 되므로)")
    else:
        print("  실패 사례 없음 — 지금 골든셋 기준으로는 엘보우가 정답을 자른 적이 없음.")
        print("  (min_k를 도입할 근거가 약함 — 표본을 더 늘려 재확인 권장)")

    # --- CSV 저장 ---
    out_dir = "data/test_results"
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"score_distribution_{ts}.csv")
    fieldnames = ["id", "question", "gold_rank", "max_gap_after_rank"] + [f"score_{i+1}" for i in range(TOP_K)]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\n원점수 전부 저장됨: {out_path} (스프레드시트로 직접 그려볼 수 있음)")


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_CSVS
    run(paths)