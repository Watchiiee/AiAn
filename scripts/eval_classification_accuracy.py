"""
분류 정확도(Accuracy) 평가 - 체크포인트4 핵심.

data/classification_labels_draft.csv(gold_type/gold_category가 채워진 최종
검토본)를 읽어, 각 질문을 실제 classify()에 다시 돌려서 예측값과 정답을
비교한다.

department는 별도 gold 라벨을 만들지 않는다 - BusinessCategory가 실제
협회 조직도 부서에 1:1로 고정 매핑되어 있으므로(rule_engine._DEPT_MAP),
gold_category로부터 "정답 부서"를 그대로 유도할 수 있다. 이렇게 하면
평가 로직이 프로덕션 로직(apply_rules)을 그대로 재사용하게 되어, 매핑을
따로 중복 관리하다 둘이 어긋나는 위험도 없다.

reviewed 안 된(gold_type/gold_category가 비어있는) 행은 평가대상에서
자동으로 제외한다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_classification_accuracy
"""
import sys
import os
import csv
import time

sys.path.insert(0, os.getcwd())

from AI.classifier.classifier import classify  # noqa: E402
from BE.rules.rule_engine import apply_rules  # noqa: E402
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory  # noqa: E402

LABELS_FILE = "data/classification_labels_draft.csv"


def run():
    if not os.path.exists(LABELS_FILE):
        print(f"라벨 파일이 없습니다: {LABELS_FILE}")
        print("먼저 scripts/generate_classification_labels_draft.py로 초안을 만들고,")
        print("gold_type/gold_category를 채운 뒤 다시 실행하세요.")
        return

    with open(LABELS_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    total = 0
    skipped = 0
    type_correct = 0
    category_correct = 0
    domain_correct = 0
    department_correct = 0
    mismatches = []

    for idx, row in enumerate(rows):
        print(f"[{idx+1}/{len(rows)}] {row['id']} 처리 중...")
        gold_type_raw = row.get("gold_type", "").strip()
        gold_category_raw = row.get("gold_category", "").strip()
        gold_domain_raw = row.get("gold_domain", "").strip()

        if not gold_type_raw or not gold_category_raw or not gold_domain_raw:
            skipped += 1
            continue

        try:
            gold_type = InquiryType(gold_type_raw)
            gold_category = BusinessCategory(gold_category_raw)
            gold_domain = Domain(gold_domain_raw)
        except ValueError as e:
            print(f"[{row['id']}] 라벨 값이 Enum과 안 맞음(오타 확인 필요): {e}")
            skipped += 1
            continue

        total += 1

        cls = classify(row["question"])
        time.sleep(1.0)  # rate limit(42901) 방지 - 문항당 2회 호출(도메인+메인)이라
                          # 쉬지 않고 연달아 돌리면 CLOVA 분당 요청한도를 넘김(실측 확인됨)

        # 정답 부서는 gold_category를 그대로 apply_rules()에 태워서 유도
        # (별도 매핑 하드코딩 없이 프로덕션 로직 그대로 재사용)
        gold_cls_for_rule = Classification(
            type=gold_type, key_request="", confidence=1.0,
            domain=gold_domain, category=gold_category, is_relevant=True,
        )
        gold_rule = apply_rules(row["question"], gold_cls_for_rule)
        pred_rule = apply_rules(row["question"], cls)

        is_type_ok = cls.type == gold_type
        is_category_ok = cls.category == gold_category
        is_domain_ok = cls.domain == gold_domain
        is_dept_ok = pred_rule.department == gold_rule.department

        type_correct += is_type_ok
        category_correct += is_category_ok
        domain_correct += is_domain_ok
        department_correct += is_dept_ok

        if not (is_type_ok and is_category_ok and is_domain_ok and is_dept_ok):
            mismatches.append({
                "id": row["id"],
                "question": row["question"][:50],
                "gold": f"{gold_type.value}/{gold_category.value}/{gold_domain.value}/{gold_rule.department}",
                "pred": f"{cls.type.value}/{cls.category.value}/{cls.domain.value}/{pred_rule.department}",
            })

    if total == 0:
        print("평가 가능한 항목이 없습니다(전부 미검토 상태). 라벨링을 먼저 완료하세요.")
        return

    print("=" * 70)
    print(f"분류 정확도 평가 결과 (평가대상 {total}건, 미검토 제외 {skipped}건)")
    print("=" * 70)
    print(f"유형(type) 정확도:       {type_correct}/{total} ({type_correct/total:.1%})")
    print(f"업무영역(category) 정확도: {category_correct}/{total} ({category_correct/total:.1%})")
    print(f"도메인(domain) 정확도:    {domain_correct}/{total} ({domain_correct/total:.1%})")
    print(f"담당부서(department) 정확도: {department_correct}/{total} ({department_correct/total:.1%})")

    if mismatches:
        print(f"\n불일치 {len(mismatches)}건 (형식: 유형/업무영역/도메인/부서):")
        for m in mismatches:
            print(f"  [{m['id']}] {m['question']}")
            print(f"      정답: {m['gold']}")
            print(f"      예측: {m['pred']}")


if __name__ == "__main__":
    run()