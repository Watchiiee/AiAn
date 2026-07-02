"""
LLM 호출을 한곳에 모은다.
지금은 Google Gemini 사용. 나중에 Claude/CLOVA로 바꾸려면
이 파일의 call_llm() 내부만 갈아끼우면 된다 (classifier/generator는 그대로).
키가 없으면 호출하지 않고 None을 돌려준다 (호출부에서 더미로 대체).
"""
from typing import Optional
from BE.core.config import settings

_client = None


def _get_client():
    global _client
    if not settings.has_api_key:
        return None
    if _client is None:
        # import를 함수 안에 둬서, 키가 없으면 라이브러리 로딩도 안 한다.
        from google import genai
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def call_llm(model: str, system: str, user: str, max_tokens: int = 1024) -> Optional[str]:
    """
    LLM에 한 번 질의하고 텍스트를 돌려준다.
    키가 없으면 None (호출부에서 더미 응답으로 대체).
    system(지시)과 user(질문)를 합쳐서 보낸다.
    """
    client = _get_client()
    if client is None:
        return None

    from google.genai import types

    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            temperature=0.2,  # 분류·근거기반 답변이라 낮게 (덜 창의적, 더 일관적)
        ),
    )
    return (resp.text or "").strip()