"""
decompose_query()의 오분해율(단일질문을 잘못 여러 개로 쪼개는 비율)을 측정.

파이프라인 배선(node_retrieve 통합 등)은 아직 하지 않은 상태 — 이 함수 하나만
독립적으로 골든셋 89개에 돌려서, "단일질문(A/B/E/F유형, 84개)을 잘못 쪼개지
않는지"를 먼저 확인한다. 이게 낮아야 파이프라인 배선을 진행할 근거가 생긴다
(M-4/O-6에서 반복된 원칙: 국소기능을 배선하기 전에 그 기능 자체의 부작용부터
저비용으로 확인).

C유형(복합질문, 5개: H04/G04/M04/M05/MT05)은 "제대로 분해하는지"를 참고로만
확인(이번 측정의 핵심은 아님 — 핵심은 나머지 84개의 오분해율).

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_decompose_misclass
"""
import csv
import os
import sys

sys.path.insert(0, os.getcwd())

from AI.rag.grading import decompose_query  # noqa: E402

DEFAULT_CSVS = ["data/golden_dataset_phase1.csv", "data/golden_dataset_phase2.csv", "data/golden_dataset_bias_probe.csv"]


def load_golden_set() -> list[dict]:
    rows = []
    for path in DEFAULT_CSVS:
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def run():
    rows = load_golden_set()
    single_type_rows = [r for r in rows if r["type"] != "C"]
    compound_rows = [r for r in rows if r["type"] == "C"]

    print(f"단일질문(비C유형) {len(single_type_rows)}개, 복합질문(C유형) {len(compound_rows)}개\n")

    # --- 핵심: 단일질문 오분해율 ---
    print("=" * 70)
    print("단일질문 오분해 검사 (이게 낮아야 함 — 핵심 지표)")
    print("=" * 70)
    misclassified = []
    for r in single_type_rows:
        sub_qs = decompose_query(r["question"])
        is_split = len(sub_qs) > 1
        mark = "⚠️ 잘못 쪼개짐" if is_split else "OK"
        print(f"[{r['id']}] {mark} | {r['question'][:40]}")
        if is_split:
            misclassified.append((r["id"], r["question"], sub_qs))

    print(f"\n오분해 개수: {len(misclassified)}/{len(single_type_rows)} "
          f"({len(misclassified)/len(single_type_rows):.1%})")
    if misclassified:
        print("\n오분해된 항목 상세:")
        for qid, q, subs in misclassified:
            print(f"  [{qid}] {q}")
            for s in subs:
                print(f"      -> {s}")

    # --- 참고: 복합질문 분해 성공률 ---
    print("\n" + "=" * 70)
    print("복합질문 분해 검사 (참고용 — 이번 측정의 핵심은 아님)")
    print("=" * 70)
    correctly_split = 0
    for r in compound_rows:
        sub_qs = decompose_query(r["question"])
        is_split = len(sub_qs) > 1
        mark = "OK(분해됨)" if is_split else "분해 안 됨"
        print(f"[{r['id']}] {mark} | {r['question'][:40]} -> {sub_qs}")
        if is_split:
            correctly_split += 1
    print(f"\n복합질문 분해 성공: {correctly_split}/{len(compound_rows)}")

    print("\n" + "=" * 70)
    print("결론 가이드")
    print("=" * 70)
    print("오분해율이 낮으면(예: 5% 이하) -> 파이프라인 배선(node_retrieve 통합) 진행 검토 가능")
    print("오분해율이 높으면 -> 프롬프트를 더 보수적으로 조정하거나, 이 기능 자체를 보류")


if __name__ == "__main__":
    run()