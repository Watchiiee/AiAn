"""
LLM 호출을 한곳에 모은다.
지금은 Google Gemini 사용. 나중에 Claude/CLOVA로 바꾸려면
이 파일의 call_llm() 내부만 갈아끼우면 된다 (classifier/generator는 그대로).

반환 규칙:
  - 키가 없으면 None (호출부에서 '더미'로 대체)
  - 호출 중 오류(429 한도초과, 503 서버혼잡 등)면 LLMError 예외 (짧은 사유 포함)
  - 성공하면 텍스트
"""
from typing import Optional
from BE.core.config import settings

_client = None


class LLMError(Exception):
    """LLM 호출 실패. 짧은 사유(예: '429 RESOURCE_EXHAUSTED')를 담는다."""
    pass


def _get_client():
    global _client
    if not settings.has_api_key:
        return None
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _short_reason(e: Exception) -> str:
    """긴 에러에서 앞부분(코드/상태)만 짧게 뽑는다."""
    msg = str(e).split("{")[0].strip().rstrip(".")
    if not msg:
        msg = type(e).__name__
    return msg[:120]


def call_llm(model: str, system: str, user: str, max_tokens: int = 2048) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None  # 키 없음 → 호출부에서 더미로 대체

    from google.genai import types

    # 제미나이 2.5 계열은 답변 전 'thinking'에도 토큰을 쓴다.
    # 분류·근거기반 답변엔 불필요하므로 꺼서 토큰을 답변에만 쓴다.
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    try:
        resp = client.models.generate_content(model=model, contents=user, config=config)
    except Exception as e:
        # 429/503/네트워크 등 → 짧은 사유를 담아 LLMError로 (500으로 죽지 않게)
        raise LLMError(_short_reason(e))

    return (resp.text or "").strip()