"""
LLM 호출을 한곳에 모은다.
기본: 네이버 CLOVA Studio (HyperCLOVA X, HCX-005) 사용.
실험적: Upstage Solar (OpenAI 호환 형식) — 채점기 계열에서 시험 적용 가능
(BE/core/config.py의 grader_provider/grader_model, DECISION_LOG 참고).
"""
from typing import Optional, Generator
import json
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


def call_llm_stream(
    model: str, system: str, user: str, max_tokens: int = 2048, provider: str = "clova",
) -> Generator[str, None, None]:
    """
    call_llm()의 스트리밍 버전 - 완성된 응답을 한 번에 반환하지 않고, 텍스트
    조각(delta)이 생성되는 대로 순서대로 yield한다. 담당자 코파일럿처럼 실시간
    대화 느낌이 필요한 곳에서만 쓴다. 기존 call_llm()과 완전히 독립된 별도
    함수라, 채점기 등 기존 호출자들은 전혀 영향받지 않는다.
    """
    if provider == "upstage":
        yield from _stream_upstage(model, system, user, max_tokens)
    else:
        yield from _stream_clova(model, system, user, max_tokens)


def _stream_clova(model: str, system: str, user: str, max_tokens: int) -> Generator[str, None, None]:
    if not settings.has_api_key:
        return

    url = _CLOVA_URL.format(model=model)
    headers = {
        "Authorization": f"Bearer {settings.clova_api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "maxCompletionTokens": max_tokens,
        "temperature": 0.2,
        "topP": 0.8,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, stream=True, timeout=60)
    except requests.exceptions.Timeout:
        raise LLMError("TIMEOUT (60초 초과)")
    except Exception as e:
        raise LLMError(f"요청 실패: {str(e)[:80]}")

    # 실측 확인됨(scripts/debug_clova_stream.py, DECISION_LOG 참고): CLOVA는
    # SSE에서 "event:" 줄로 종류를 구분한다 —
    #   event:token  -> delta(그때그때 새로 추가된 글자만), 이것만 이어붙이면 됨
    #   event:result -> 스트림이 끝난 뒤 "전체 답변 전체"를 통째로 한 번 더
    #                    보냄(중복이므로 반드시 무시할 것 - 안 그러면 답변이
    #                    두 배로 붙는다)
    #   event:signal -> 종료 신호({"data":"[DONE]"}), 무시하고 루프 종료
    current_event = None
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
            continue
        if not line or not line.startswith("data:"):
            continue
        if current_event != "token":
            continue  # event:result(전체 재전송), event:signal(종료신호)은 무시
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        delta = data.get("message", {}).get("content", "")
        if delta:
            yield delta


def _stream_upstage(model: str, system: str, user: str, max_tokens: int) -> Generator[str, None, None]:
    if not settings.upstage_api_key.strip():
        return

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
        "stream": True,
    }

    try:
        resp = requests.post(_UPSTAGE_URL, headers=headers, json=body, stream=True, timeout=60)
    except requests.exceptions.Timeout:
        raise LLMError("TIMEOUT (60초 초과)")
    except Exception as e:
        raise LLMError(f"요청 실패: {str(e)[:80]}")

    # Upstage는 OpenAI 호환 스트리밍 형식(delta.content, 종료 시 "data: [DONE]")
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choices = data.get("choices", [])
        if not choices:
            continue
        delta = choices[0].get("delta", {}).get("content")
        if delta:
            yield delta