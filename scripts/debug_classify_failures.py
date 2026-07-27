"""
eval_classification_accuracy.py 재측정에서 category/department 정확도가
86.5%->34.8%로 급락한 원인 진단. classify()의 except LLMError 블록이
에러를 조용히 삼켜버려서(_fallback()으로만 떨어짐) 원인이 콘솔에 안 보이므로,
call_llm()을 직접 호출해서 실패 원인을 그대로 노출시킨다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_classify_failures
"""
import sys
import os
import time

sys.path.insert(0, os.getcwd())

from AI.llm import call_llm, LLMError  # noqa: E402
from AI.prompts import CLASSIFIER_SYSTEM  # noqa: E402
from BE.core.config import settings  # noqa: E402

TEST_QUESTIONS = [
    "P2-01에서 계속 실패한 질문 재현용",
    "회원가입 절차는 어떻게 되나요?",
    "교육 신청(일정·비용 등 확인)은 어떻게 하나요?",
    "CT 2차를 열어놓으면 왜 위험한가요?",
    "안전관리자 선임신고 어떻게 하나요?",
]


def run():
    print(f"모델: {settings.classifier_model}\n")
    success = 0
    fail = 0
    for i, q in enumerate(TEST_QUESTIONS):
        start = time.time()
        try:
            raw = call_llm(settings.classifier_model, CLASSIFIER_SYSTEM, q, max_tokens=256)
            elapsed = time.time() - start
            success += 1
            print(f"[{i+1}] 성공 ({elapsed:.2f}초): {q[:30]}")
            print(f"    응답: {raw[:150]}")
        except LLMError as e:
            elapsed = time.time() - start
            fail += 1
            print(f"[{i+1}] 실패 ({elapsed:.2f}초): {q[:30]}")
            print(f"    LLMError 원문: {e}")
        print()

    print(f"성공 {success}/{len(TEST_QUESTIONS)}, 실패 {fail}/{len(TEST_QUESTIONS)}")


if __name__ == "__main__":
    run()