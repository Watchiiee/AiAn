"""
hallucination_grade를 CLOVA 단독 vs Upstage Solar 단독으로 비교.

A~D는 정답(expected_grounded)이 명확해 recall(B/C/D를 얼마나 잡아내는지)과
false positive rate(A를 잘못 걸러내는 비율)를 계산한다. E(부분일치/모호)는
정답이 없다 — 두 모델이 이 모호한 지점을 어떻게 다르게 판단하는지만 참고로 본다.

실행 (레포 루트에서, venv 활성화 후 — 25개 x 2공급자 = 50회 LLM 호출):
    python3 -m scripts.eval_hallucination_providers
"""
import csv
import os
import sys

sys.path.insert(0, os.getcwd())

from BE.core.schemas import RetrievedDoc  # noqa: E402

CSV_PATH = "data/hallucination_test_set.csv"


def load_test_set() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def run_provider(provider: str, model: str, rows: list[dict]) -> list[dict]:
    import BE.core.config as cfg
    cfg.settings.hallucination_grader_provider = provider
    cfg.settings.hallucination_grader_model = model
    import importlib
    if "AI.rag.grading" in sys.modules:
        importlib.reload(sys.modules["AI.rag.grading"])
    from AI.rag.grading import grade_hallucination

    print(f"\n{'='*70}\n공급자: {provider} (model={model})\n{'='*70}")
    results = []
    for r in rows:
        docs = [RetrievedDoc(content=r["gold_chunk_content"], source="test", score=0.9)]
        grounded = grade_hallucination(r["test_answer"], docs)
        results.append({"id": r["id"], "category": r["category"], "domain": r["domain"], "grounded": grounded})
        print(f"[{r['category']}][{r['id']}] grounded={grounded}")
    return results


def _expected(rows: list[dict]) -> dict:
    return {r["id"]: (r["expected_grounded"] == "TRUE") for r in rows if r["expected_grounded"] != ""}


def summarize(results: list[dict], expected: dict, label: str):
    print(f"\n--- {label} ---")
    # A(정상, grounded=True 기대) 대상 false positive rate
    a_results = [r for r in results if r["category"] == "A"]
    a_fp = sum(1 for r in a_results if not r["grounded"])  # True인데 False로 잘못 걸러냄
    print(f"A(정상답변) false positive: {a_fp}/{len(a_results)} "
          f"({a_fp/len(a_results):.1%} — 정상인데 잘못 걸러낸 비율, 낮아야 좋음)")

    # B/C/D(hallucination, grounded=False 기대) recall
    bcd_results = [r for r in results if r["category"] in ("B", "C", "D")]
    bcd_caught = sum(1 for r in bcd_results if not r["grounded"])  # False로 정확히 잡아냄
    print(f"B/C/D(hallucination) recall: {bcd_caught}/{len(bcd_results)} "
          f"({bcd_caught/len(bcd_results):.1%} — 진짜 문제를 잡아낸 비율, 높아야 좋음)")

    # 카테고리별 세부
    from collections import defaultdict
    by_cat = defaultdict(lambda: {"total": 0, "grounded_true": 0})
    for r in results:
        by_cat[r["category"]]["total"] += 1
        if r["grounded"]:
            by_cat[r["category"]]["grounded_true"] += 1
    for cat in sorted(by_cat):
        c = by_cat[cat]
        print(f"  카테고리 {cat}: {c['total']}개 중 grounded=True {c['grounded_true']}개")

    return {"a_fp_rate": a_fp / len(a_results), "bcd_recall": bcd_caught / len(bcd_results)}


def run():
    rows = load_test_set()
    expected = _expected(rows)
    print(f"테스트셋 {len(rows)}개 로드 (정답 있는 A~D: {len(expected)}개, E는 참고용)")

    clova_results = run_provider("clova", os.environ.get("CLOVA_HALLUC_MODEL", "HCX-005"), rows)
    upstage_results = run_provider("upstage", os.environ.get("UPSTAGE_HALLUC_MODEL", "solar-pro2"), rows)

    print("\n" + "=" * 70)
    print("최종 비교")
    print("=" * 70)
    s_clova = summarize(clova_results, expected, "CLOVA")
    s_upstage = summarize(upstage_results, expected, "Upstage Solar")

    print("\n" + "=" * 70)
    print(f"{'':<20}{'CLOVA':<15}{'Upstage':<15}")
    print(f"{'A false positive':<20}{s_clova['a_fp_rate']:<15.1%}{s_upstage['a_fp_rate']:<15.1%}")
    print(f"{'B/C/D recall':<20}{s_clova['bcd_recall']:<15.1%}{s_upstage['bcd_recall']:<15.1%}")

    # E(모호) 항목에서 두 모델이 다르게 판단한 것만 별도 출력
    print("\n" + "=" * 70)
    print("E(부분일치/모호) — 두 모델의 판단이 갈린 항목")
    print("=" * 70)
    e_clova = {r["id"]: r["grounded"] for r in clova_results if r["category"] == "E"}
    e_upstage = {r["id"]: r["grounded"] for r in upstage_results if r["category"] == "E"}
    for qid in e_clova:
        c, u = e_clova[qid], e_upstage[qid]
        mark = "  <-- 판단 갈림" if c != u else ""
        print(f"[{qid}] CLOVA={c}, Upstage={u}{mark}")


if __name__ == "__main__":
    run()