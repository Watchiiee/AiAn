"""
LLM 호출을 한곳에 모은다.
현재: 네이버 CLOVA Studio (HyperCLOVA X, HCX-005) 사용.
과거: Google Gemini (아래에 주석으로 보존 — 되돌리려면 이 파일만 교체).

반환 규칙 (classifier/generator 는 이 규칙에만 의존하므로 안 바뀐다):
  - 키가 없으면 None            → 호출부에서 '더미'로 대체
  - 호출 실패(429/503 등)면 LLMError (짧은 사유 포함)
  - 성공하면 텍스트
"""
import json
from typing import Optional
from BE.core.config import settings


class LLMError(Exception):
    """LLM 호출 실패. 짧은 사유(예: '42901 RATE_LIMIT')를 담는다."""
    pass


# =====================================================================
# 현재 사용: CLOVA Studio (HyperCLOVA X)
# =====================================================================
import requests

_CLOVA_URL = "https://clovastudio.stream.ntruss.com/v3/chat-completions/{model}"


def call_llm(model: str, system: str, user: str, max_tokens: int = 2048) -> Optional[str]:
    if not settings.has_api_key:
        return None  # 키 없음 → 호출부에서 더미로 대체

    url = _CLOVA_URL.format(model=model)
    headers = {
        "Authorization": f"Bearer {settings.clova_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "maxCompletionTokens": max_tokens,
        "temperature": 0.2,   # 분류·근거기반 답변이라 낮게 (덜 창의적, 더 일관적)
        "topP": 0.8,
        # 참고: "thinking"은 추론 모델(HCX-007 등)에서만 지원.
        # HCX-005는 미지원이라 넣으면 40001 오류 → 제거함.
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        data = resp.json()
    except requests.exceptions.Timeout:
        raise LLMError("TIMEOUT (30초 초과)")
    except Exception as e:
        raise LLMError(f"요청 실패: {str(e)[:80]}")

    # CLOVA는 성공/실패 모두 200으로 오고, status.code 로 구분한다.
    code = str(data.get("status", {}).get("code", ""))
    if code != "20000":
        msg = data.get("status", {}).get("message", "알 수 없는 오류")
        raise LLMError(f"{code} {msg}"[:120])

    return (data["result"]["message"]["content"] or "").strip()


# =====================================================================
# (보존) 이전 사용: Google Gemini
#   되돌리려면 위 CLOVA 블록을 주석 처리하고 아래 주석을 해제.
#   .env 의 GEMINI_API_KEY / CLASSIFIER_MODEL(gemini-...) 도 함께 되살릴 것.
# =====================================================================
# _client = None
#
# def _get_client():
#     global _client
#     if not settings.has_api_key:
#         return None
#     if _client is None:
#         from google import genai
#         _client = genai.Client(api_key=settings.gemini_api_key)
#     return _client
#
# def call_llm(model: str, system: str, user: str, max_tokens: int = 2048) -> Optional[str]:
#     client = _get_client()
#     if client is None:
#         return None
#     from google.genai import types
#     config = types.GenerateContentConfig(
#         system_instruction=system,
#         max_output_tokens=max_tokens,
#         temperature=0.2,
#         thinking_config=types.ThinkingConfig(thinking_budget=0),
#     )
#     try:
#         resp = client.models.generate_content(model=model, contents=user, config=config)
#     except Exception as e:
#         msg = str(e).split("{")[0].strip().rstrip(".") or type(e).__name__
#         raise LLMError(msg[:120])
#     return (resp.text or "").strip()