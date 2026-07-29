"""
멘토링 피드백 대응 - "카테고리당 5~10개의 정제된 질문/프롬프트 사전 정의"를
발표 당일 실시간 타이핑 대신 미리 프로그램으로 돌려서 결과 리포트로 준비한다.

이미 체크포인트4 대응(BB절)으로 골든셋에 gold_category 라벨을 달아뒀으므로,
새 질문을 만들 필요 없이 그 라벨을 그대로 재사용해 카테고리별로 그룹핑한다 -
이미 신뢰도가 검증된 문항이라 데모용으로도 안전하다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.generate_demo_scenarios

출력: docs/demo_scenarios_report.md
"""
import sys
import os
import csv
import time
from collections import defaultdict

sys.path.insert(0, os.getcwd())

from BE.api.pipeline import process_inquiry  # noqa: E402

LABELS_FILE = "data/classification_labels_draft.csv"
OUTPUT_FILE = "docs/demo_scenarios_report.md"
QUESTIONS_PER_CATEGORY = 5


def load_questions_by_category() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    with open(LABELS_FILE, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cat = row.get("gold_category", "").strip()
            question = row.get("question", "").strip()
            if cat and question:
                grouped[cat].append(question)
    return grouped


def run():
    grouped = load_questions_by_category()
    total_questions = sum(min(len(qs), QUESTIONS_PER_CATEGORY) for qs in grouped.values())
    print(f"카테고리 {len(grouped)}개, 총 {total_questions}건 실행 예정\n")

    lines = ["# 카테고리별 시연 질문세트 실행 결과\n",
             "> 멘토링 피드백 대응 - 카테고리당 최대 5개, 골든셋(gold_category 라벨) 재사용\n"]

    done = 0
    for cat, questions in sorted(grouped.items()):
        selected = questions[:QUESTIONS_PER_CATEGORY]
        lines.append(f"\n## {cat} ({len(selected)}건)\n")

        for q in selected:
            done += 1
            print(f"[{done}/{total_questions}] ({cat}) {q[:40]}...")

            try:
                resp = process_inquiry(q)
            except Exception as e:
                lines.append(f"### 질문: {q}\n- **실패**: {e}\n")
                time.sleep(1.5)
                continue

            flag = "⚠️ " if resp.answer_confidence.value == "insufficient" else ""
            lines.append(f"### {flag}질문: {q}")
            lines.append(f"- 유형: `{resp.classification.type.value}` / 부서: `{resp.rule.department}` / 우선순위: `{resp.rule.priority}`")
            lines.append(f"- 확신도: `{resp.answer_confidence.value}` / 검색된 근거문서: {len(resp.retrieved)}건")
            preview = resp.answer_draft[:120].replace("\n", " ")
            lines.append(f"- 답변 미리보기: {preview}...")
            lines.append("")

            time.sleep(1.5)  # rate limit 방지 (BB-9에서 확정된 방식과 동일)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n완료 -> {OUTPUT_FILE}")
    print("⚠️ 표시가 붙은 항목(확신도 insufficient)은 발표 시연에서 제외하는 것을 권장합니다.")


if __name__ == "__main__":
    run()