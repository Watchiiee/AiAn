"""
classify() 리팩터링(도메인 분류 분리) 전/후로 domain 이외 필드
(category, key_request, confidence, is_relevant)가 안정적으로 유지되는지 확인하는 스크립트.

사용법:
  1. 분리 작업 "전"(지금 코드)에서:
       python3 -m scripts.check_classification_stability snapshot data/test_results/before.json
  2. classifier.py/prompts.py를 분리 구조로 수정
  3. 분리 작업 "후"에:
       python3 -m scripts.check_classification_stability compare data/test_results/before.json

결과: domain 필드는 비교하지 않음(바뀌는 게 정상이니까). category/key_request/
confidence/is_relevant 중 하나라도 달라진 문항을 표로 보여줌.

주의: LLM 호출 특성상 confidence는 약간의 숫자 흔들림이 정상(예: 0.85→0.87).
      완전히 다른 값으로 바뀌었거나, category/is_relevant가 바뀐 경우만 실제
      회귀로 보면 된다.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from AI.classifier.classifier import classify  # noqa: E402

CSV_PATHS = [
    "data/golden_dataset_phase1.csv",
    "data/golden_dataset_phase2.csv",
    "data/golden_dataset_bias_probe.csv",
]


def _load_questions() -> list[dict]:
    rows = []
    for path in CSV_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))
    return rows


def snapshot(out_path: str):
    rows = _load_questions()
    print(f"{len(rows)}개 질문에 대해 classify() 호출 중...")
    results = {}
    for r in rows:
        cls = classify(r["question"])
        results[r["id"]] = {
            "question": r["question"],
            "category": cls.category.value,
            "key_request": cls.key_request,
            "confidence": cls.confidence,
            "is_relevant": cls.is_relevant,
        }
        print(f"  [{r['id']}] category={cls.category.value}, is_relevant={cls.is_relevant}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n스냅샷 저장됨: {out_path}")


def compare(before_path: str):
    with open(before_path, encoding="utf-8") as f:
        before = json.load(f)

    rows = _load_questions()
    print(f"{len(rows)}개 질문에 대해 classify() 재호출 중 (분리 후)...")

    diffs = []
    for r in rows:
        qid = r["id"]
        if qid not in before:
            continue
        cls = classify(r["question"])
        after = {
            "category": cls.category.value,
            "key_request": cls.key_request,
            "confidence": cls.confidence,
            "is_relevant": cls.is_relevant,
        }
        b = before[qid]
        changed = []
        if after["category"] != b["category"]:
            changed.append(f"category: {b['category']} -> {after['category']}")
        if after["is_relevant"] != b["is_relevant"]:
            changed.append(f"is_relevant: {b['is_relevant']} -> {after['is_relevant']}")
        if abs(after["confidence"] - b["confidence"]) > 0.15:
            changed.append(f"confidence: {b['confidence']} -> {after['confidence']} (큰 변화)")
        if changed:
            diffs.append({"id": qid, "question": r["question"][:40], "changed": changed})

    print("\n" + "=" * 70)
    if not diffs:
        print("변화 없음 — category/is_relevant/confidence 전부 안정적으로 유지됨.")
    else:
        print(f"{len(diffs)}개 항목에서 변화 감지:")
        for d in diffs:
            print(f"\n[{d['id']}] {d['question']}")
            for c in d["changed"]:
                print(f"    - {c}")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    mode, path = sys.argv[1], sys.argv[2]
    if mode == "snapshot":
        snapshot(path)
    elif mode == "compare":
        compare(path)
    else:
        print("첫 인자는 'snapshot' 또는 'compare' 여야 합니다.")