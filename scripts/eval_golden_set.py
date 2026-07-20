"""
골든 데이터셋 기반 평가 스크립트 (v2 — 여러 CSV 인자 지원 + phase별 집계).

Phase1(위험도기반 심층진단)과 Phase2(baseline sanity check)는 목적이 달라
물리적으로 합치지 않고, 각 CSV의 'phase' 컬럼으로 구분한 채 런타임에만 합쳐서
평가한다. 이렇게 하면:
  - 전체 합산 지표와 phase별 지표를 모두 볼 수 있음 (Phase2가 baseline이라
    recall이 Phase1보다 낮게 나와도 "전체가 나빠졌다"는 오해를 방지)
  - 나중에 Phase3(실사용 로그 기반)가 생겨도 CSV만 추가하면 됨 (물리적 병합
    불필요, 원본 파일 각각 독립적으로 안전하게 관리)

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_golden_set
    python3 -m scripts.eval_golden_set data/golden_dataset_phase1.csv data/golden_dataset_phase2.csv
    python3 -m scripts.eval_golden_set data/golden_dataset_phase3.csv   # Phase3 추가 시 이렇게만 하면 됨

인자를 안 주면 기본값(phase1.csv, phase2.csv 둘 다)을 사용한다.

결과: 콘솔 출력(전체 + phase별) + data/test_results/golden_eval_<시각>.md 저장.
(data/test_results/는 로컬 전용 — 깃허브에 커밋하지 않기로 함, DECISION_LOG L절 참고)
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.getcwd())

from AI.classifier.classifier import classify  # noqa: E402
from AI.rag.retriever import retrieve  # noqa: E402
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory  # noqa: E402

DEFAULT_CSVS = ["data/golden_dataset_phase1.csv", "data/golden_dataset_phase2.csv"]
TOP_K = 10
HIT_KS = (1, 3, 5, 10)


def load_golden_set(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        with open(path, encoding="utf-8-sig") as f:
            file_rows = list(csv.DictReader(f))
        for r in file_rows:
            if not r.get("phase"):
                r["phase"] = os.path.basename(path).replace(".csv", "")
        rows.extend(file_rows)
        print(f"  {path}: {len(file_rows)}개 로드")
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
        type=InquiryType.GENERAL, key_request="golden set 평가용", confidence=1.0,
        domain=Domain(domain), category=BusinessCategory.OTHER, is_relevant=True,
    )


def eval_retrieval(rows: list[dict]) -> list[dict]:
    print("\n" + "=" * 70)
    print("1. 검색(retrieval) 품질 평가 — classify() 없이 retrieve()만 호출")
    print("=" * 70)

    results = []
    for r in rows:
        gold_pairs = _parse_gold_chunks(r["gold_chunk_id"])
        cls = _dummy_classification(r["gold_domain"])
        docs = retrieve(r["question"], cls, top_k=TOP_K)
        retrieved_pairs = [_parse_retrieved_source(d.source) for d in docs]

        ranks = []
        for gp in gold_pairs:
            rank = -1
            for i, rp in enumerate(retrieved_pairs, 1):
                if rp == gp:
                    rank = i
                    break
            ranks.append(rank)

        found = sum(1 for rk in ranks if rk > 0)
        recall = found / len(gold_pairs) if gold_pairs else 0.0
        max_rank = max(ranks) if all(rk > 0 for rk in ranks) else None

        results.append({
            "id": r["id"], "phase": r["phase"], "type": r["type"],
            "question": r["question"][:40], "n_gold": len(gold_pairs), "found": found,
            "recall": recall, "ranks": ranks, "all_found_max_rank": max_rank,
        })
        rank_str = ", ".join(str(rk) if rk > 0 else "미검출" for rk in ranks)
        print(f"[{r['phase']}][{r['id']}] recall {found}/{len(gold_pairs)} | 순위: {rank_str} | {r['question'][:40]}")

    return results


def eval_domain_classification(rows: list[dict]) -> list[dict]:
    print("\n" + "=" * 70)
    print("2. 도메인 분류(classification) 품질 평가 — classify() 실제 호출 (LLM 사용)")
    print("=" * 70)

    results = []
    for r in rows:
        cls = classify(r["question"])
        correct = cls.domain.value == r["gold_domain"]
        results.append({
            "id": r["id"], "phase": r["phase"], "type": r["type"], "question": r["question"][:40],
            "gold_domain": r["gold_domain"], "predicted_domain": cls.domain.value, "correct": correct,
        })
        mark = "OK" if correct else "MISS"
        print(f"[{mark}] [{r['phase']}][{r['id']}] gold={r['gold_domain']:<10} predicted={cls.domain.value:<10} | {r['question'][:40]}")

    return results


def _summarize_retrieval(results: list[dict]) -> dict:
    if not results:
        return {"avg_recall": 0.0, "hits": {k: 0 for k in HIT_KS}, "total": 0}
    hits = {k: 0 for k in HIT_KS}
    for res in results:
        if res["all_found_max_rank"] is not None:
            for k in HIT_KS:
                if res["all_found_max_rank"] <= k:
                    hits[k] += 1
    avg_recall = sum(r["recall"] for r in results) / len(results)
    return {"avg_recall": avg_recall, "hits": hits, "total": len(results)}


def _summarize_domain(results: list[dict]) -> dict:
    if not results:
        return {"total": 0, "n_correct": 0, "f_total": 0, "f_correct": 0}
    total = len(results)
    n_correct = sum(1 for r in results if r["correct"])
    f_type = [r for r in results if r["type"] == "F"]
    f_correct = sum(1 for r in f_type if r["correct"])
    return {"total": total, "n_correct": n_correct, "f_total": len(f_type), "f_correct": f_correct}


def _print_retrieval_summary(label: str, summary: dict):
    if summary["total"] == 0:
        return
    print(f"\n--- [{label}] 검색 품질 요약 (n={summary['total']}) ---")
    print(f"평균 recall: {summary['avg_recall']:.1%}")
    for k in HIT_KS:
        h = summary["hits"][k]
        print(f"Hit@{k}: {h}/{summary['total']} ({h/summary['total']:.1%})")


def _print_domain_summary(label: str, summary: dict):
    if summary["total"] == 0:
        return
    print(f"\n--- [{label}] 도메인 분류 요약 (n={summary['total']}) ---")
    print(f"전체 정확도: {summary['n_correct']}/{summary['total']} ({summary['n_correct']/summary['total']:.1%})")
    if summary["f_total"]:
        print(f"F유형(경계형) 정확도: {summary['f_correct']}/{summary['f_total']} ({summary['f_correct']/summary['f_total']:.1%})")


def run(csv_paths: list[str]):
    print("골든셋 로드 중:")
    rows = load_golden_set(csv_paths)
    phase_counts = {}
    for r in rows:
        phase_counts[r["phase"]] = phase_counts.get(r["phase"], 0) + 1
    print(f"총 {len(rows)}개 문항 (phase 분포: {phase_counts})")

    retrieval_results = eval_retrieval(rows)
    domain_results = eval_domain_classification(rows)

    phases = sorted(set(r["phase"] for r in rows))

    print("\n" + "#" * 70)
    print("### 전체 요약 ###")
    print("#" * 70)
    _print_retrieval_summary("전체", _summarize_retrieval(retrieval_results))
    _print_domain_summary("전체", _summarize_domain(domain_results))

    per_phase_retrieval = {}
    per_phase_domain = {}
    for p in phases:
        r_res = [r for r in retrieval_results if r["phase"] == p]
        d_res = [r for r in domain_results if r["phase"] == p]
        per_phase_retrieval[p] = _summarize_retrieval(r_res)
        per_phase_domain[p] = _summarize_domain(d_res)
        print(f"\n{'#' * 70}")
        print(f"### {p} 요약 ###")
        print("#" * 70)
        _print_retrieval_summary(p, per_phase_retrieval[p])
        _print_domain_summary(p, per_phase_domain[p])

    out_dir = "data/test_results"
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"golden_eval_{ts}.md")

    def _write_retrieval_section(f, label, summary):
        f.write(f"### {label} (n={summary['total']})\n\n")
        if summary["total"]:
            f.write(f"- 평균 recall: {summary['avg_recall']:.1%}\n")
            for k in HIT_KS:
                h = summary["hits"][k]
                f.write(f"- Hit@{k}: {h}/{summary['total']} ({h/summary['total']:.1%})\n")
        f.write("\n")

    def _write_domain_section(f, label, summary):
        f.write(f"### {label} (n={summary['total']})\n\n")
        if summary["total"]:
            f.write(f"- 전체 정확도: {summary['n_correct']}/{summary['total']} ({summary['n_correct']/summary['total']:.1%})\n")
            if summary["f_total"]:
                f.write(f"- F유형 정확도: {summary['f_correct']}/{summary['f_total']} ({summary['f_correct']/summary['f_total']:.1%})\n")
        f.write("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# 골든셋 평가 결과 ({ts})\n\n")
        f.write(f"대상 CSV: {', '.join(csv_paths)}\n\n")

        f.write("## 1. 검색 품질\n\n")
        _write_retrieval_section(f, "전체", _summarize_retrieval(retrieval_results))
        for p in phases:
            _write_retrieval_section(f, p, per_phase_retrieval[p])
        f.write("| id | phase | type | recall | 순위 | 질문 |\n|---|---|---|---|---|---|\n")
        for r in retrieval_results:
            rank_str = ", ".join(str(rk) if rk > 0 else "미검출" for rk in r["ranks"])
            f.write(f"| {r['id']} | {r['phase']} | {r['type']} | {r['found']}/{r['n_gold']} | {rank_str} | {r['question']} |\n")

        f.write("\n## 2. 도메인 분류 품질\n\n")
        _write_domain_section(f, "전체", _summarize_domain(domain_results))
        for p in phases:
            _write_domain_section(f, p, per_phase_domain[p])
        f.write("| id | phase | type | 정답도메인 | 예측도메인 | 결과 | 질문 |\n|---|---|---|---|---|---|---|\n")
        for r in domain_results:
            mark = "O" if r["correct"] else "X"
            f.write(f"| {r['id']} | {r['phase']} | {r['type']} | {r['gold_domain']} | {r['predicted_domain']} | {mark} | {r['question']} |\n")

    print(f"\n결과 저장됨: {out_path}")


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_CSVS
    run(paths)