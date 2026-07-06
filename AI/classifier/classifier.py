"""
1단계: LLM 분류.
문의 텍스트 → 유형 + 핵심요청을 JSON으로 추출한다.
키가 없거나 LLM 호출이 실패하면 키워드 기반 간이 분류로 폴백한다.
(분류는 실패해도 시스템이 멈추지 않게 조용히 폴백 — 품질만 낮아짐)
프롬프트는 AI/prompts.py 에 분리해 두었다.
"""
import json
from AI.llm import call_llm, LLMError
from AI.prompts import CLASSIFIER_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, InquiryType

_FALLBACK_KEYWORDS = {
    InquiryType.CAREER_CERT: ["경력", "경력증명", "경력인증", "수첩"],
    InquiryType.ERROR: ["로그인", "오류", "안 됩니다", "에러", "장애", "접속"],
    InquiryType.CANCEL_REFUND: ["취소", "환불"],
    InquiryType.CHANGE: ["변경", "수정", "바꾸"],
    InquiryType.APPLY: ["신청", "발급", "재직증명"],
    InquiryType.URGENT: ["급", "마감", "당장", "즉시"],
}


def _fallback(text: str) -> Classification:
    for itype, words in _FALLBACK_KEYWORDS.items():
        if any(w in text for w in words):
            return Classification(type=itype, key_request=text[:50], confidence=0.3)
    return Classification(type=InquiryType.GENERAL, key_request=text[:50], confidence=0.2)


def _normalize_confidence(value) -> float:
    """
    모델마다 confidence 단위가 다르다 (0~1 소수 vs 0~100 백분율).
    - Gemini 등: 0.9
    - CLOVA HCX-005 등: 90
    어느 쪽이 와도 0~1 범위로 맞춘다. 1보다 크면 100으로 나눈다.
    """
    try:
        c = float(value)
    except (TypeError, ValueError):
        return 0.5
    if c > 1:
        c = c / 100.0
    return max(0.0, min(1.0, c))  # 0~1 범위로 안전하게 제한


def classify(text: str) -> Classification:
    try:
        raw = call_llm(settings.classifier_model, CLASSIFIER_SYSTEM, text, max_tokens=256)
    except LLMError:
        # LLM 호출 실패(429/503 등) → 키워드 폴백으로 조용히 대체
        return _fallback(text)

    if raw is None:  # 키 없음 → 폴백
        return _fallback(text)

    try:
        data = json.loads(raw)
        return Classification(
            type=InquiryType(data["type"]),
            key_request=data.get("key_request", text[:50]),
            confidence=_normalize_confidence(data.get("confidence", 0.5)),
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        return _fallback(text)