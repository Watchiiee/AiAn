"""
의심되는 질문들에 대해 classify_domain()을 여러 번(기본 5회) 반복 호출해,
결과가 매번 같게 나오는지(= 결정론적, 특정 표현 패턴 문제) 아니면 왔다갔다
하는지(= 확률적 노이즈)를 구분하는 스크립트.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.repeat_check_domain
    python3 -m scripts.repeat_check_domain --n 10   # 반복 횟수 조정
"""
import sys
import os
import argparse
from collections import Counter

sys.path.insert(0, os.getcwd())

from AI.classifier.classifier import classify_domain  # noqa: E402

# (id, 질문, 정답 도메인) — 이번 평가에서 실패했거나 대조가 필요한 항목들
TEST_CASES = [
    ("P2-11", "특고압 인입선로(22,900V)의 전류를 저압(600V)용 후크온미터로 측정하면 안 되는 이유는 무엇인가요?", "technical"),
    ("P2-12", "22.9kV 선로를 저압용 클램프미터로 측정해도 되나요?", "technical"),
    ("P2-23", "-20~-45℃ 급냉실용 등기구·램프는 어떤 것을 선정해야 하나요?", "technical"),
    ("P2-24", "냉동창고에는 어떤 조명을 써야 하나요?", "technical"),
    ("P2-29", "옥외용 파워퓨즈를 옥내(변압기가 설치된 실내)에 설치해서 사용해도 되나요?", "technical"),
    ("P2-30", "파워퓨즈 옥외용을 옥내에서 써도 되나요?", "technical"),
    # '~해도 되나요' 형식 패턴이 파워퓨즈 주제에만 국한된 건지, 더 넓은 패턴인지 확인용 (다른 주제, 같은 문장형식)
    ("NEW-01", "지중에 매설된 전선관에 이음매(커플링)를 두어도 안전한가요?", "technical"),
    ("NEW-02", "3상3선식 냉동기에 전력량계를 설치할 때, 3상4선식 계량기의 N상만 빼고 결선해도 되나요?", "technical"),
]


def run(n: int):
    print(f"각 질문당 {n}회 반복 호출\n")
    print("=" * 90)

    for qid, question, gold in TEST_CASES:
        results = []
        for i in range(n):
            d = classify_domain(question)
            results.append(d.value)

        counts = Counter(results)
        is_stable = len(counts) == 1
        matches_gold = counts.most_common(1)[0][0] == gold

        if is_stable and matches_gold:
            verdict = "안정적으로 정답"
        elif is_stable and not matches_gold:
            verdict = "⚠️ 안정적으로 오답 — 노이즈가 아니라 특정 표현 패턴 문제로 재분류 필요"
        else:
            verdict = "🔀 결과가 흔들림 — 확률적 노이즈로 보임"

        print(f"[{qid}] {question[:50]}")
        print(f"  정답: {gold} | 결과 분포: {dict(counts)} | 판정: {verdict}")
        print("-" * 90)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5, help="반복 횟수 (기본 5)")
    args = parser.parse_args()
    run(args.n)