"""
1단계: LLM 분류.
문의 텍스트 → 유형 + 핵심요청을 JSON으로 추출한다.
키가 없으면 키워드 기반 간이 분류로 폴백 (1주차 데모용).
프롬프트는 AI/prompts.py 에 분리해 두었다.
"""
import json
from AI.llm import call_llm
from AI.prompts import CLASSIFIER_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, InquiryType

# 키 없을 때 쓰는 아주 단순한 키워드 폴백 (LLM 분류의 대용은 아님)
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


def classify(text: str) -> Classification:
    raw = call_llm(settings.classifier_model, CLASSIFIER_SYSTEM, text, max_tokens=256)

    if raw is None:  # 키 없음 → 폴백
        return _fallback(text)

    try:
        data = json.loads(raw)
        return Classification(
            type=InquiryType(data["type"]),
            key_request=data.get("key_request", text[:50]),
            confidence=float(data.get("confidence", 0.5)),
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        # LLM이 형식을 어기거나 모르는 유형을 뱉으면 안전하게 폴백
        return _fallback(text)