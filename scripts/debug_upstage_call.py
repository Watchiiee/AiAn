"""
Upstage Solar 호출이 (트리비얼 테스트에서는 성공했는데) 실제 25개 채점에서는
왜 매번 False만 나오는지 진단. 이번엔 트리비얼한 질문이 아니라, 실제
HALLUCINATION_GRADER_SYSTEM 프롬프트 + 테스트셋의 진짜 근거문서/답변 하나를
그대로 보내서 원본 응답을 확인한다 — _safe_bool_call()의 에러처리(파싱실패시
조용히 False)를 거치지 않고, requests.post()의 원본 응답을 그대로 출력한다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_upstage_call
"""
import sys
import os
import json
import csv

sys.path.insert(0, os.getcwd())

import requests  # noqa: E402
from BE.core.config import settings  # noqa: E402
from AI.prompts import HALLUCINATION_GRADER_SYSTEM  # noqa: E402

# 실제 실패했던 카테고리 A(완전일치, grounded=True가 나와야 정상) 중 하나를 그대로 사용
TEST_ROW_ID = "HG-B01"


def run():
    print(f"upstage_api_key 설정 여부: {bool(settings.upstage_api_key.strip())}")
    print(f"hallucination_grader_model: {settings.hallucination_grader_model}")
    print()

    with open("data/hallucination_test_set.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    row = next(r for r in rows if r["id"] == TEST_ROW_ID)

    docs_text = f"- {row['gold_chunk_content']}"
    user = f"[근거 문서]\n{docs_text}\n\n[생성된 답변]\n{row['test_answer']}"

    print(f"테스트 항목: {TEST_ROW_ID} (기대값: grounded={row['expected_grounded']})")
    print(f"실제 system 프롬프트:\n{HALLUCINATION_GRADER_SYSTEM}\n")
    print(f"실제 user 프롬프트:\n{user}\n")
    print("=" * 70)

    url = "https://api.upstage.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.upstage_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.hallucination_grader_model,
        "messages": [
            {"role": "system", "content": HALLUCINATION_GRADER_SYSTEM},
            {"role": "user", "content": user},
        ],
        "max_tokens": 500,
        "temperature": 0.2,
        "top_p": 0.8,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
    except Exception as e:
        print(f"requests.post() 자체가 예외를 던짐: {type(e).__name__}: {e}")
        return

    print(f"HTTP 상태 코드: {resp.status_code}")
    print()

    try:
        data = resp.json()
    except Exception as e:
        print(f"JSON 파싱 실패: {e}")
        print("원본 텍스트:", resp.text[:1000])
        return

    print("전체 응답 구조:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print()

    try:
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason")
        completion_tokens = data.get("usage", {}).get("completion_tokens")
        reasoning_tokens = data.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens")
        print(f"content 필드만: {content!r}")
        print(f"finish_reason: {finish_reason} (length면 max_tokens에서 잘렸다는 뜻)")
        print(f"completion_tokens: {completion_tokens}, reasoning_tokens: {reasoning_tokens}")
        print()
        try:
            parsed = json.loads(content.strip())
            print(f"content를 순수 JSON으로 파싱: 성공 -> {parsed}")
        except json.JSONDecodeError as e:
            print(f"content를 순수 JSON으로 파싱: 실패 -> {e}")
            print("(이게 실패하면 _safe_bool_call도 똑같이 실패해서 default=False로 떨어진다)")
    except (KeyError, IndexError) as e:
        print(f"응답 구조가 예상과 다름: {e}")


if __name__ == "__main__":
    run()