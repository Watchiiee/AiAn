"""
담당자 코파일럿(StaffPage 사이드바 대화형 도우미) 파일럿 검증.

아직 파이프라인에 배선하지 않은 상태 — 실제 문의 3건(가상이지만 실제
지식베이스 내용 기반)에 대해, "정상 범위 질문"(이미 있는 컨텍스트로 답 가능)과
"범위 이탈 질문"(새 검색/조회가 필요)을 섞어서 던져보고:
① 정상 질문에 실제로 컨텍스트 기반의 구체적인 답을 하는지
② 범위 이탈 질문에서 지어내지 않고 정확히 정해진 거절 문구로 답하는지
③ 응답 속도가 실사용에 무리 없는 수준인지(초 단위 측정)
④ 컨텍스트에 없는 문서 번호를 지어내지 않는지(인덱스 정확성) — 1차 파일럿에서
   실제로 걸린 문제(존재하지 않는 "2번 문서" 언급)라, 프롬프트 보강 후 이게
   노이즈였는지 반복되는 패턴이었는지 5회 반복으로 확인한다(O-5/O-6과 같은 방법).

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_copilot_pilot
"""
import sys
import os
import time
import re
from collections import Counter

sys.path.insert(0, os.getcwd())

from AI.llm import call_llm, LLMError  # noqa: E402
from AI.prompts import COPILOT_SYSTEM  # noqa: E402
from BE.core.config import settings  # noqa: E402

REFUSAL_PHRASE = "이 기능은 아직 지원하지 않습니다"
N_REPEATS = 5

# --- 가상 문의 컨텍스트 3건 (실제 지식베이스 내용 기반, 이번 세션 골든셋 재활용) ---
SCENARIOS = [
    {
        "name": "P2-06 (CT 2차 개방 위험, technical)",
        "num_docs": 4,
        "context": """[원본 문의] CT 2차를 열어놓으면 왜 위험한가요?
[분류] technical / 기술지원 / 일반문의
[검색된 문서 전체]
  [0] (선택됨) CT는 승압 트랜스와 동일한 원리로 동작합니다. 2차 개방시 감자작용 소멸로 1차전류 전체가 여자전류가 되어 권수비에 비례한 고전압이 2차에 유도됩니다. — 출처: knowledge_ct_pt_mof.md
  [1] (선택 안 됨) CT 소음의 주원인은 대전류 통전 시 발생하는 전자기력입니다. — 출처: knowledge_ct_pt_mof.md
  [2] (선택 안 됨) CTT(CT 시험단자)를 이용하면 정전 없이 작업할 수 있습니다. — 출처: knowledge_current_voltage_power.md
  [3] (선택 안 됨) 각상 CT 2차의 두 가닥을 Y결선 없이... — 출처: knowledge_relay.md
[생성된 답변] CT(변류기)는 승압 트랜스와 동일한 원리로 동작하기 때문에, 2차측을 개방하면 감자작용이 사라져 1차 전류 전체가 여자전류가 되고, 권수비에 비례한 고전압이 2차측에 유도되어 위험합니다.
[확신도] sufficient""",
        "questions": [
            ("왜 0번 문서를 선택했어?", "in_scope"),
            ("1번, 2번 문서는 왜 선택 안 됐어?", "in_scope"),
            ("답변에서 '권수비에 비례한 고전압'이라는 부분은 어느 문서에서 나온 내용이야?", "in_scope"),
            ("이거랑 비슷한 예전 문의 사례 찾아줘", "out_of_scope"),
            ("이 문의를 다른 부서로 옮겨도 될까?", "out_of_scope"),
        ],
    },
    {
        "name": "G05 (IEEE Std 142 접지저항, technical, 확신도 partial)",
        "num_docs": 1,
        "context": """[원본 문의] IEEE Std 142 기준으로 공통접지 접지저항은 몇 옴이어야 하나요?
[분류] technical / 기술지원 / 일반문의
[검색된 문서 전체]
  [0] (선택됨) IEEE Std 142, ANSI/NFPA 70·780 기준으로 대용량 교환장비 1~2옴, 일반 통신장비 2~5옴, 산업용 변전설비 1~5옴 등 장비별로 다르게 권장됩니다. — 출처: knowledge_grounding.md
[생성된 답변] IEEE Std 142 기준으로 공통접지 접지저항은 연결되는 장비 종류에 따라 다르며, 일반적으로 1~5옴 수준으로 권장됩니다. 정확한 값은 장비별 기준을 확인해야 합니다.
[확신도] partial""",
        "questions": [
            ("왜 확신도가 partial로 나왔어?", "in_scope"),
            ("근거문서가 1개밖에 없는데 이게 맞는거야?", "in_scope"),
            ("접지 관련 다른 근거 문서도 더 찾아봐줘", "out_of_scope"),
        ],
    },
    {
        "name": "P2-45 (교육 신청, admin)",
        "num_docs": 2,
        "context": """[원본 문의] 교육 신청(일정·비용 등 확인)은 어떻게 하나요?
[분류] admin / 교육 / 일반문의
[검색된 문서 전체]
  [0] (선택됨) 협회 홈페이지 로그인 후 교육원(교육신청) > 교육신청 > 과정·지역·일정 선택 > 결제 순으로 진행합니다. — 출처: knowledge_education.md
  [1] (선택 안 됨) 컨소시엄 훈련의 대상은 재직자 및 구직자입니다. — 출처: knowledge_consortium.md
[생성된 답변] 협회 홈페이지에 로그인한 후 교육원(교육신청) 메뉴에서 원하는 과정·지역·일정을 선택하고 결제하면 신청이 완료됩니다.
[확신도] sufficient""",
        "questions": [
            ("1번 문서(컨소시엄훈련)는 왜 선택 안 됐어?", "in_scope"),
            ("이 사람이 예전에도 교육 문의한 적 있는지 이력 보여줘", "out_of_scope"),
        ],
    },
]


def _check_index_out_of_range(response: str, num_docs: int) -> list[int]:
    """응답에서 언급된 문서번호(N번, [N]) 중 컨텍스트 범위(0~num_docs-1)를
    벗어나는 것들을 찾아 반환한다. 비어있으면 인덱스 관련 문제 없음."""
    mentioned = set()
    for m in re.finditer(r"\[(\d+)\]", response):
        mentioned.add(int(m.group(1)))
    for m in re.finditer(r"(\d+)\s*번\s*문서", response):
        mentioned.add(int(m.group(1)))
    return sorted(i for i in mentioned if i < 0 or i >= num_docs)


def run():
    print(f"각 질문당 {N_REPEATS}회 반복 호출\n")

    total_in = 0
    total_out = 0
    ok_in = 0
    ok_out = 0
    index_issue_questions = []

    for scenario in SCENARIOS:
        print("=" * 80)
        print(f"시나리오: {scenario['name']} (문서 {scenario['num_docs']}개: [0]~[{scenario['num_docs']-1}])")
        print("=" * 80)

        for question, expected in scenario["questions"]:
            user = f"{scenario['context']}\n\n[담당자 질문] {question}"
            print(f"[{expected}] Q: {question}")

            refusal_results = []
            index_issue_results = []
            elapsed_list = []

            for i in range(N_REPEATS):
                start = time.time()
                try:
                    raw = call_llm(settings.classifier_model, COPILOT_SYSTEM, user, max_tokens=400)
                except LLMError as e:
                    print(f"  [{i+1}회차] LLM 호출 실패: {e}")
                    continue
                elapsed = time.time() - start
                elapsed_list.append(elapsed)

                is_refusal = REFUSAL_PHRASE in (raw or "")
                refusal_results.append(is_refusal)

                bad_idx = _check_index_out_of_range(raw or "", scenario["num_docs"])
                index_issue_results.append(bool(bad_idx))
                idx_note = f" ⚠️ 범위밖 번호 언급: {bad_idx}" if bad_idx else ""
                print(f"  [{i+1}회차] {elapsed:.2f}초, 거절={is_refusal}{idx_note}")

            n = len(refusal_results)
            if n == 0:
                continue
            avg_elapsed = sum(elapsed_list) / len(elapsed_list)
            refusal_rate = sum(refusal_results) / n
            index_issue_rate = sum(index_issue_results) / n

            if expected == "out_of_scope":
                total_out += 1
                verdict = "✅ 안정적으로 거절" if refusal_rate == 1.0 else (
                    "🔀 거절 흔들림(노이즈 가능성)" if 0 < refusal_rate < 1.0 else "⚠️ 안정적으로 거절 실패")
                if refusal_rate == 1.0:
                    ok_out += 1
            else:
                total_in += 1
                verdict = "✅ 안정적으로 정상답변" if refusal_rate == 0.0 else "⚠️ 정상질문인데 거절됨"
                if refusal_rate == 0.0:
                    ok_in += 1

            if index_issue_rate > 0:
                index_verdict = f"⚠️ 인덱스 범위밖 언급 {sum(index_issue_results)}/{n}회"
                index_issue_questions.append((scenario["name"], question, index_issue_rate))
            else:
                index_verdict = "✅ 인덱스 문제 없음"

            print(f"  => 평균 {avg_elapsed:.2f}초 | {verdict} | {index_verdict}\n")

    print("=" * 80)
    print("전체 요약")
    print("=" * 80)
    print(f"정상범위 질문: {ok_in}/{total_in} 안정적으로 정상답변")
    print(f"범위이탈 질문: {ok_out}/{total_out} 안정적으로 거절")
    if index_issue_questions:
        print(f"\n인덱스 범위밖 언급이 발생한 질문 {len(index_issue_questions)}건:")
        for name, q, rate in index_issue_questions:
            print(f"  [{name}] {q} -> {rate:.0%} 비율로 발생")
        print("\n판정: 이 비율이 1회차 파일럿과 비교해 줄었으면 프롬프트 보강이 효과 있었다는 뜻.")
        print("      여전히 반복적으로 나오면(특히 100%에 가까우면) 노이즈가 아니라")
        print("      구조적 문제 -> 프롬프트 재설계 또는 문서목록을 더 명확한 형식으로 변경 필요.")
    else:
        print("\n인덱스 범위밖 언급: 5회 반복 전부에서 발생하지 않음 - 프롬프트 보강이 효과적이었음.")


if __name__ == "__main__":
    run()