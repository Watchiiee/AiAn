"""
답변적합도(Answer Suitability) 평가 - 체크포인트4의 나머지 절반.

골든셋 89개 질문을 실제 전체 파이프라인(process_inquiry)에 그대로 돌려서
두 가지 신호를 집계한다:
  1. answer_confidence 분포 - 이미 파이프라인 내부에서 hallucination_grade/
     answer_grade 게이트를 거친 결과가 반영된 값(추가 LLM 호출 없이 얻어짐)
  2. gold_answer 대비 정확성 - ANSWER_CORRECTNESS_SYSTEM으로 별도 채점.
     confidence만으로는 "검색이 틀린 문서를 찾아 일관되게 인용한 경우"를
     못 잡아내므로(내부적으로는 일관되니 confidence는 높게 나옴), 정답과의
     실제 일치 여부를 독립적으로 한 번 더 확인해야 진짜 "적합도"가 된다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.eval_answer_suitability
"""
import sys
import os
import csv
import time
from collections import Counter

sys.path.insert(0, os.getcwd())

from BE.api.pipeline import process_inquiry  # noqa: E402
from AI.llm import call_llm, LLMError  # noqa: E402
from AI.prompts import ANSWER_CORRECTNESS_SYSTEM  # noqa: E402
from BE.core.config import settings  # noqa: E402

SOURCE_FILES = [
    "data/golden_dataset_phase1.csv",
    "data/golden_dataset_phase2.csv",
    "data/golden_dataset_bias_probe.csv",
]


def _grade_correctness(generated: str, gold_answer: str) -> bool | None:
    user = f"[정답]\n{gold_answer}\n\n[생성된 답변]\n{generated}"
    raw = None
    for attempt in range(2):
        try:
            raw = call_llm(settings.classifier_model, ANSWER_CORRECTNESS_SYSTEM, user, max_tokens=64)
            break
        except LLMError as e:
            is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
            if attempt == 0:
                time.sleep(5.0 if is_rate_limit else 0.5)
            continue
    if raw is None:
        return None
    import json
    try:
        return bool(json.loads(raw.strip()).get("correct", False))
    except (json.JSONDecodeError, AttributeError):
        return None


def run():
    rows = []
    for src in SOURCE_FILES:
        if not os.path.exists(src):
            continue
        with open(src, encoding="utf-8-sig") as f:
            rows.extend(list(csv.DictReader(f)))

    confidence_dist = Counter()
    correctness_results = []  # (id, is_correct or None)
    failures = []

    for idx, row in enumerate(rows):
        question = row["question"]
        gold_answer = row["gold_answer"]

        print(f"[{idx+1}/{len(rows)}] {row['id']} 처리 중... (전체 파이프라인, 문항당 여러 LLM호출)")

        try:
            response = process_inquiry(question)
        except Exception as e:
            print(f"[{row['id']}] process_inquiry 실패: {e}")
            failures.append(row["id"])
            continue
        finally:
            # 문항당 LLM 호출이 많아(분류·긴급판단·문서채점·생성·검증2개, 재시도
            # 포함하면 10회 이상 가능) classify()보다 훨씬 rate limit에 취약함
            # - 실측으로 확인된 rate limit 문제(DECISION_LOG 참고) 재발 방지용
            time.sleep(2.0)

        confidence_dist[response.answer_confidence.value] += 1

        is_correct = _grade_correctness(response.answer_draft, gold_answer)
        correctness_results.append((row["id"], is_correct))

        mark = "?" if is_correct is None else ("O" if is_correct else "X")
        print(f"[{row['id']}] confidence={response.answer_confidence.value}, 정답일치={mark}")

    total = len(correctness_results)
    graded = [r for _, r in correctness_results if r is not None]
    correct_count = sum(1 for r in graded if r)
    ungraded_count = total - len(graded)

    print("\n" + "=" * 70)
    print(f"답변적합도 평가 결과 (총 {total}건, 파이프라인 실패 {len(failures)}건 제외)")
    print("=" * 70)
    print(f"확신도(answer_confidence) 분포: {dict(confidence_dist)}")
    print(f"  - sufficient 비율: {confidence_dist['sufficient']/total:.1%}")
    if graded:
        print(f"정답 대비 정확성(ANSWER_CORRECTNESS): {correct_count}/{len(graded)} ({correct_count/len(graded):.1%})")
    if ungraded_count:
        print(f"  (채점 실패로 집계에서 제외된 건: {ungraded_count}건)")

    incorrect_ids = [i for i, r in correctness_results if r is False]
    if incorrect_ids:
        print(f"\n정답과 불일치한 문항 ID: {incorrect_ids}")


if __name__ == "__main__":
    run()