"""
골든셋에 gold_type/gold_category(→ gold_department는 rule_engine으로 자동
유도되므로 별도 컬럼 불필요)를 추가하기 위한 "검토용 초안" 생성 스크립트.

콜드 라벨링(89개를 아예 처음부터 손으로 다는 것) 대신, 현재 classify()의
예측을 초안(draft)으로 만들어서 사람이 검토·수정하는 방식으로 시간을
아낀다. 단, 이건 "AI가 자기 시험문제 답을 미리 보는" 순환 위험이 있으므로
반드시 사람이 각 항목을 실제로 검토·수정해야 한다 - 초안을 그냥 승인만
하면 골든셋으로서의 신뢰성이 없어진다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.generate_classification_labels_draft

출력: data/classification_labels_draft.csv
  - id, question, gold_domain(기존), draft_type, draft_category(AI 예측)
  - gold_type, gold_category(사람이 채워야 할 빈 칸)
  - reviewed(검토 완료 표시용, 기본 빈 칸)
"""
import sys
import os
import csv

sys.path.insert(0, os.getcwd())

from AI.classifier.classifier import classify  # noqa: E402

SOURCE_FILES = [
    "data/golden_dataset_phase1.csv",
    "data/golden_dataset_phase2.csv",
    "data/golden_dataset_bias_probe.csv",
]
OUTPUT_FILE = "data/classification_labels_draft.csv"


def run():
    rows_out = []
    for src in SOURCE_FILES:
        if not os.path.exists(src):
            print(f"[스킵] {src} 없음")
            continue
        with open(src, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = row["question"]
                try:
                    cls = classify(question)
                    draft_type = cls.type.value
                    draft_category = cls.category.value
                except Exception as e:
                    draft_type = f"(분류실패: {e})"
                    draft_category = ""

                rows_out.append({
                    "id": row["id"],
                    "question": question,
                    "gold_domain": row.get("gold_domain", ""),
                    "draft_type": draft_type,
                    "draft_category": draft_category,
                    "gold_type": "",       # 사람이 채울 최종 정답 (draft 보고 맞으면 그대로 복사, 틀리면 수정)
                    "gold_category": "",   # 사람이 채울 최종 정답
                    "reviewed": "",        # 검토 완료하면 y로 표시
                })
                print(f"[{row['id']}] {question[:40]}... -> type={draft_type}, category={draft_category}")

    with open(OUTPUT_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "question", "gold_domain", "draft_type", "draft_category",
            "gold_type", "gold_category", "reviewed",
        ])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\n총 {len(rows_out)}건 -> {OUTPUT_FILE} 생성 완료")
    print("다음 단계: 스프레드시트로 열어서 draft_type/draft_category를 검토하고,")
    print("각 행마다 gold_type/gold_category를 채운 뒤 reviewed에 y를 표시하세요.")
    print("(맞으면 draft 값을 그대로 복사, 틀렸으면 올바른 값으로 수정)")
    print()
    print('InquiryType 후보값: 경력인증 / 신청 / 변경 / "취소/환불" / "오류/장애" / 일반문의 / 긴급문의 / 미분류')
    print("BusinessCategory 후보값: 전기안전관리자/설계감리/경력회원/공제사업/교육/컨소시엄훈련/홈페이지·전산/기술지원/기타")


if __name__ == "__main__":
    run()