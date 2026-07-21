"""
P2-06("CT 2차를 열어놓으면 왜 위험한가요?")이 individual 모드에서 선택=0으로 나온
원인을 진단하는 스크립트. grade_documents_individual()의 파싱된 결과만 보지 않고,
채점기를 5회 반복 호출해 "안정적으로 틀림(진짜 문제)"인지 "확률적으로 흔들림(노이즈,
O-5/O-6과 같은 패턴)"인지 구분한다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_doc_grade_p206
"""
import sys
import os
from collections import Counter

sys.path.insert(0, os.getcwd())

from AI.llm import call_llm, LLMError  # noqa: E402
from AI.prompts import DOC_GRADER_SYSTEM_INDIVIDUAL  # noqa: E402
from AI.rag.retriever import retrieve  # noqa: E402
from BE.core.config import settings  # noqa: E402
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory  # noqa: E402

QUESTION = "CT 2차를 열어놓으면 왜 위험한가요?"
GOLD_KEYWORD = "구동 중 2차측을 개방"  # P2-06 정답청크 헤딩에 포함된 키워드
N_REPEATS = 5


def run():
    cls = Classification(
        type=InquiryType.GENERAL, key_request="진단용", confidence=1.0,
        domain=Domain.TECHNICAL, category=BusinessCategory.OTHER, is_relevant=True,
    )
    docs = retrieve(QUESTION, cls)

    print(f"질문: {QUESTION}")
    print(f"검색된 문서 {len(docs)}개:\n")
    gold_idx = None
    for i, d in enumerate(docs):
        marker = ""
        if GOLD_KEYWORD in d.source:
            marker = "  <-- 정답청크"
            gold_idx = i
        print(f"[{i}] (검색점수={d.score}) {d.source}{marker}")
    print(f"\n정답청크 인덱스: {gold_idx}\n")

    docs_text = "\n".join(f"[{i}] (검색점수={d.score}) {d.content}" for i, d in enumerate(docs))
    user = f"[질문] {QUESTION}\n\n[검색된 문서 목록]\n{docs_text}"

    print("=" * 70)
    print(f"{N_REPEATS}회 반복 호출")
    print("=" * 70)

    results = []
    for i in range(N_REPEATS):
        try:
            raw = call_llm(settings.classifier_model, DOC_GRADER_SYSTEM_INDIVIDUAL, user, max_tokens=128)
        except LLMError as e:
            print(f"  [{i+1}회차] LLM 호출 실패: {e}")
            results.append("호출실패")
            continue
        print(f"  [{i+1}회차] 원본 응답: {raw!r}")
        results.append(raw)

    print("\n" + "=" * 70)
    print("판정")
    print("=" * 70)
    gold_included = []
    for raw in results:
        if raw == "호출실패":
            gold_included.append(False)
            continue
        included = gold_idx is not None and f"{gold_idx}" in raw.replace(" ", "")
        gold_included.append(included)
    counts = Counter(gold_included)
    print(f"정답청크 포함 여부 분포: {dict(counts)}")
    if len(counts) == 1:
        verdict = "안정적으로 포함됨(문제없음)" if True in counts and False not in counts else "⚠️ 안정적으로 배제됨 — 노이즈가 아니라 진짜 문제, 프롬프트/문서 표현 재검토 필요"
    else:
        verdict = "🔀 결과가 흔들림 — 확률적 노이즈로 보임(O-5/O-6과 같은 패턴)"
    print(f"판정: {verdict}")


if __name__ == "__main__":
    run()



if __name__ == "__main__":
    run()