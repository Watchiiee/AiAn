"""
CLOVA Studio 스트리밍 응답의 실제 SSE 형식을 직접 확인하는 스크립트.
_stream_clova()가 가정한 형식(매 줄 "data: {...}", message.content가 누적인지
delta인지)이 실제와 맞는지 원본 그대로 출력해서 확인한다 — 맞지 않으면
AI/llm.py의 _stream_clova()를 이 결과에 맞게 수정해야 한다.

실행 (레포 루트에서, venv 활성화 후):
    python3 -m scripts.debug_clova_stream
"""
import sys
import os

sys.path.insert(0, os.getcwd())

import requests  # noqa: E402
from BE.core.config import settings  # noqa: E402

_CLOVA_URL = "https://clovastudio.stream.ntruss.com/v3/chat-completions/{model}"


def run():
    model = settings.classifier_model
    print(f"clova_api_key 설정 여부: {bool(settings.clova_api_key.strip())}")
    print(f"모델: {model}\n")

    url = _CLOVA_URL.format(model=model)
    headers = {
        "Authorization": f"Bearer {settings.clova_api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "messages": [
            {"role": "system", "content": "너는 친절한 도우미다. 3문장 이내로 짧게 답하라."},
            {"role": "user", "content": "오늘 날씨가 좋네요라고 인사해줘"},
        ],
        "maxCompletionTokens": 100,
        "temperature": 0.2,
        "topP": 0.8,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, stream=True, timeout=30)
    except Exception as e:
        print(f"요청 실패: {type(e).__name__}: {e}")
        return

    print(f"HTTP 상태 코드: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}\n")
    print("=" * 70)
    print("원본 SSE 라인 (한 줄씩, 빈 줄도 그대로 표시)")
    print("=" * 70)

    line_count = 0
    for line in resp.iter_lines(decode_unicode=True):
        line_count += 1
        print(f"[{line_count}] {line!r}")

    print(f"\n총 {line_count}줄 수신")
    print("\n해석 가이드:")
    print("- 'data:' 뒤 JSON의 message.content가 매번 '전체 텍스트'로 커지면 -> 누적 방식")
    print("- 매번 '새로 추가된 글자만' 오면 -> delta 방식")
    print("- 'event:' 필드가 있고 종류(예: token/result/signal)가 다르면 -> 이벤트별 분기 처리가 필요할 수 있음")
    print("- 위 두 가지를 확인해서 AI/llm.py의 _stream_clova()가 맞게 처리하고 있는지 대조할 것")


if __name__ == "__main__":
    run()