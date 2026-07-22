"""
LLM 호출을 한곳에 모은다.
기본: 네이버 CLOVA Studio (HyperCLOVA X, HCX-005) 사용.
실험적: Upstage Solar (OpenAI 호환 형식) — 채점기 계열에서 시험 적용 가능
(BE/core/config.py의 grader_provider/grader_model, DECISION_LOG 참고).
"""
from typing import Optional
from BE.core.config import settings


class LLMError(Exception):
    """LLM 호출 실패. 짧은 사유(예: '42901 RATE_LIMIT')를 담는다."""
    pass


import requests

_CLOVA_URL = "https://clovastudio.stream.ntruss.com/v3/chat-completions/{model}"
# Upstage Solar는 OpenAI 호환 chat completions 형식을 제공한다. 정확한 엔드포인트는
# Upstage 콘솔/문서에서 확인 후 필요시 이 값을 갱신할 것(API가 바뀔 수 있음).
_UPSTAGE_URL = "https://api.upstage.ai/v1/chat/completions"


def call_llm(model: str, system: str, user: str, max_tokens: int = 2048, provider: str = "clova") -> Optional[str]:
    if provider == "upstage":
        return _call_upstage(model, system, user, max_tokens)
    return _call_clova(model, system, user, max_tokens)


def _call_clova(model: str, system: str, user: str, max_tokens: int) -> Optional[str]:
    if not settings.has_api_key:
        return None

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
        "temperature": 0.2,
        "topP": 0.8,
        # 참고: "thinking"은 추론 모델(HCX-007 등)에서만 지원. HCX-005는 미지원.
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        data = resp.json()
    except requests.exceptions.Timeout:
        raise LLMError("TIMEOUT (30초 초과)")
    except Exception as e:
        raise LLMError(f"요청 실패: {str(e)[:80]}")

    code = str(data.get("status", {}).get("code", ""))
    if code != "20000":
        msg = data.get("status", {}).get("message", "알 수 없는 오류")
        raise LLMError(f"{code} {msg}"[:120])

    return (data["result"]["message"]["content"] or "").strip()


def _call_upstage(model: str, system: str, user: str, max_tokens: int) -> Optional[str]:
    """
    Upstage Solar 호출 (OpenAI 호환 형식). CLOVA와 응답 스키마가 다르므로
    별도 파서를 쓴다 — 키 이름(max_tokens vs maxCompletionTokens 등)이
    CLOVA와 다르니 혼용하지 말 것.
    """
    if not settings.upstage_api_key.strip():
        return None

    headers = {
        "Authorization": f"Bearer {settings.upstage_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "top_p": 0.8,
    }

    try:
        resp = requests.post(_UPSTAGE_URL, headers=headers, json=body, timeout=30)
        data = resp.json()
    except requests.exceptions.Timeout:
        raise LLMError("TIMEOUT (30초 초과)")
    except Exception as e:
        raise LLMError(f"요청 실패: {str(e)[:80]}")

    if "error" in data:
        msg = data["error"].get("message", "알 수 없는 오류") if isinstance(data["error"], dict) else str(data["error"])
        raise LLMError(msg[:120])

    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError):
        raise LLMError(f"응답 형식 파싱 실패: {str(data)[:100]}")