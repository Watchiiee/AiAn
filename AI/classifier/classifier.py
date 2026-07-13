"""
1단계: LLM 분류.
문의 텍스트 → 유형(type) + 도메인(domain) + 업무영역(category) + 핵심요청을 JSON으로 추출한다.
키가 없거나 LLM 호출이 실패하면 키워드 기반 간이 분류로 폴백한다.
(분류는 실패해도 시스템이 멈추지 않게 조용히 폴백 — 품질만 낮아짐. 이때
 category는 항상 OTHER로 두어 '불확실'로 명시적으로 표시한다 — 폴백값을
 확신하는 카테고리로 잘못 표시하면 안 되기 때문.)
프롬프트는 AI/prompts.py 에 분리해 두었다.
"""
import json
from AI.llm import call_llm, LLMError
from AI.prompts import CLASSIFIER_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory

_FALLBACK_KEYWORDS = {
    InquiryType.CAREER_CERT: ["경력", "경력증명", "경력인증", "수첩"],
    InquiryType.ERROR: ["로그인", "오류", "안 됩니다", "에러", "장애", "접속"],
    InquiryType.CANCEL_REFUND: ["취소", "환불"],
    InquiryType.CHANGE: ["변경", "수정", "바꾸"],
    InquiryType.APPLY: ["신청", "발급", "재직증명"],
    InquiryType.URGENT: ["급", "마감", "당장", "즉시"],
}

# LLM 실패 시 도메인 추정용 키워드 (기술 질의로 볼 만한 전기 설비 용어)
_TECH_KEYWORDS = [
    "발전기", "변압기", "차단기", "계전기", "전동기", "모터", "케이블", "배선",
    "절연", "접지", "누전", "고조파", "역률", "용량 계산", "결선", "정격",
    "과열", "과부하", "단락", "지락", "서지", "인버터", "ESS", "수배전",
]


def _guess_domain(text: str) -> Domain:
    """키워드 폴백용 도메인 추정. 전기 기술 용어가 있으면 technical, 아니면 admin."""
    return Domain.TECHNICAL if any(w in text for w in _TECH_KEYWORDS) else Domain.ADMIN


def _fallback(text: str) -> Classification:
    """
    LLM 없이 키워드로 대충 분류하는 비상용 폴백 (평소엔 안 쓰임, LLM 실패 시에만).
    category는 항상 OTHER — 키워드 매칭은 type/domain 추정도 부정확할 수 있는데
    하물며 세부 부서(category)까지 확신하는 건 위험하므로, 불확실함을 그대로 노출한다.
    (rule_engine이 OTHER를 보면 경영지원팀 + department_certain=False 로 처리)
    """
    domain = _guess_domain(text)
    for itype, words in _FALLBACK_KEYWORDS.items():
        if any(w in text for w in words):
            return Classification(
                type=itype, key_request=text[:50], confidence=0.3,
                domain=domain, category=BusinessCategory.OTHER,
            )
    return Classification(
        type=InquiryType.GENERAL, key_request=text[:50], confidence=0.2,
        domain=domain, category=BusinessCategory.OTHER,
    )


def _normalize_confidence(value) -> float:
    """
    모델마다 confidence 단위가 다르다 (0~1 소수 vs 0~100 백분율).
    - Gemini 등: 0.9 / CLOVA HCX-005 등: 90
    어느 쪽이 와도 0~1 범위로 맞춘다.
    """
    try:
        c = float(value)
    except (TypeError, ValueError):
        return 0.5
    if c > 1:
        c = c / 100.0
    return max(0.0, min(1.0, c))


def _parse_domain(value) -> Domain:
    """LLM이 준 domain 문자열을 Domain으로. 이상하면 admin(안전한 기본값)."""
    try:
        return Domain(str(value).strip().lower())
    except ValueError:
        return Domain.ADMIN


def _parse_category(value) -> BusinessCategory:
    """LLM이 준 category 문자열을 BusinessCategory로. 이상하면 OTHER(안전한 기본값)."""
    try:
        return BusinessCategory(str(value).strip())
    except ValueError:
        return BusinessCategory.OTHER


def _strip_code_fence(raw: str) -> str:
    """
    CLOVA가 프롬프트 지시("코드블록 금지")를 무시하고 ```json ... ``` 으로
    감싸서 줄 때가 있다. json.loads 전에 이걸 벗겨낸다.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]        # 첫 줄(```json 등) 제거
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def classify(text: str) -> Classification:
    try:
        raw = call_llm(settings.classifier_model, CLASSIFIER_SYSTEM, text, max_tokens=256)
    except LLMError:
        return _fallback(text)

    if raw is None:  # 키 없음 → 폴백
        return _fallback(text)

    try:
        data = json.loads(_strip_code_fence(raw))
        return Classification(
            type=InquiryType(data["type"]),
            key_request=data.get("key_request", text[:50]),
            confidence=_normalize_confidence(data.get("confidence", 0.5)),
            domain=_parse_domain(data.get("domain", "admin")),
            category=_parse_category(data.get("category", "기타")),
            is_relevant=bool(data.get("is_relevant", True)),
        )
    except (json.JSONDecodeError, ValueError, KeyError):
        return _fallback(text)