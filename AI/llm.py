"""
LLM 호출을 한곳에 모은다.
나중에 GPT로 갈아타거나 모델을 바꿀 때 여기만 손대면 된다.
키가 없으면 호출하지 않고 None을 돌려준다 (호출부에서 더미로 대체).
"""
from typing import Optional
from anthropic import Anthropic
from BE.core.config import settings

_client: Optional[Anthropic] = None


def _get_client() -> Optional[Anthropic]:
    global _client
    if not settings.has_api_key:
        return None
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def call_llm(model: str, system: str, user: str, max_tokens: int = 1024) -> Optional[str]:
    """
    LLM에 한 번 질의하고 텍스트를 돌려준다.
    키가 없으면 None (호출부에서 더미 응답으로 대체).
    """
    client = _get_client()
    if client is None:
        return None

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # content는 블록 리스트라 text 블록만 이어붙인다
    return "".join(
        block.text for block in resp.content if getattr(block, "type", None) == "text"
    ).strip()