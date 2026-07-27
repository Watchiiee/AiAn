"""
1단계: LLM 분류.
문의 텍스트 → 유형(type) + 업무영역(category) + is_relevant + 핵심요청을 JSON으로 추출한다.
도메인(domain) 판단은 이제 별도의 독립 호출(classify_domain)로 분리했다 — check_urgency와
같은 이유로, 여러 판단을 한 프롬프트에 몰아넣으면 서로 간섭한다는 것을 실제로 겪었기
때문이다(도메인 분류 예시를 추가했다가 전혀 무관한 카테고리 판단까지 깨진 사례, DECISION_LOG
N절 참고). 두 호출 결과를 합쳐 최종 Classification 객체를 만든다.
키가 없거나 LLM 호출이 실패하면 키워드 기반 간이 분류로 폴백한다.
"""
import json
import re
import time
from AI.llm import call_llm, LLMError
from AI.prompts import CLASSIFIER_SYSTEM, DOMAIN_CLASSIFIER_SYSTEM
from BE.core.config import settings
from BE.core.schemas import Classification, InquiryType, Domain, BusinessCategory


def _call_with_retry(model: str, system: str, text: str, max_tokens: int, attempts: int = 2) -> str | None:
    """
    call_llm()을 감싸서, rate limit(42901 등)을 만나면 즉시 재시도해도 소용
    없으므로(허용량이 회복될 시간이 필요) 몇 초 쉬었다가 재시도한다. 그 외의
    일시적 오류(50000 등)는 짧게 바로 재시도한다.
    실측 확인됨: 89건을 쉬지 않고 순회하면 CLOVA 분당 요청한도(rate limit)에
    실제로 걸려 특정 구간이 통째로 폴백으로 떨어지는 문제가 있었다(DECISION_LOG
    참고) - 즉시재시도만으로는 rate limit이 안 풀려서 해결이 안 됐었다.
    """
    last_error: LLMError | None = None
    for attempt in range(attempts):
        try:
            return call_llm(model, system, text, max_tokens=max_tokens)
        except LLMError as e:
            last_error = e
            is_rate_limit = "429" in str(e) or "rate" in str(e).lower()
            if attempt < attempts - 1:
                time.sleep(5.0 if is_rate_limit else 0.5)
            continue
    if last_error is not None:
        print(f"[WARN] {attempts}회 재시도 후에도 실패({last_error}): {text[:30]!r}")
    return None

_FALLBACK_KEYWORDS = {
    InquiryType.CAREER_CERT: ["경력", "경력증명", "경력인증", "수첩"],
    InquiryType.ERROR: ["로그인", "오류", "안 됩니다", "에러", "장애", "접속"],
    InquiryType.CANCEL_REFUND: ["취소", "환불"],
    InquiryType.CHANGE: ["변경", "수정", "바꾸"],
    InquiryType.APPLY: ["신청", "발급", "재직증명"],
    InquiryType.URGENT: ["급", "마감", "당장", "즉시"],
}

_TECH_KEYWORDS = [
    "발전기", "변압기", "차단기", "계전기", "전동기", "모터", "케이블", "배선",
    "절연", "접지", "누전", "고조파", "역률", "용량 계산", "결선", "정격",
    "과열", "과부하", "단락", "지락", "서지", "인버터", "ESS", "수배전",
    # eval_classification_accuracy.py 실측(89건)에서 발견된 오분류 사례 대응
    # (P2-06/P2-29/BP-03 등이 admin으로 안정적으로 오분류됨 - classify_domain이
    # 설명글을 써버려 JSON파싱이 실패하고, 키워드 폴백에서도 이 단어들이
    # 목록에 없어 기본값(admin)으로 떨어지던 것을 확인, DECISION_LOG 참고)
    "CT", "변류기", "절연저항", "접지저항", "활선", "THD", "IEEE", "PT",
]


def _guess_domain(text: str) -> Domain:
    return Domain.TECHNICAL if any(w in text for w in _TECH_KEYWORDS) else Domain.ADMIN


def _fallback(text: str) -> Classification:
    """
    LLM 없이 키워드로 대충 분류하는 비상용 폴백 (평소엔 안 쓰임, LLM 실패 시에만).
    category는 항상 OTHER, is_relevant는 항상 True — 폴백은 부정확할 수 있는데
    "잡담"으로 잘못 걸러내면(is_relevant=False) 실제 업무 문의를 놓칠 위험이 있어
    안전한 쪽(True)으로 둔다.
    """
    domain = _guess_domain(text)
    for itype, words in _FALLBACK_KEYWORDS.items():
        if any(w in text for w in words):
            return Classification(
                type=itype, key_request=text[:50], confidence=0.3,
                domain=domain, category=BusinessCategory.OTHER, is_relevant=True,
            )
    return Classification(
        type=InquiryType.GENERAL, key_request=text[:50], confidence=0.2,
        domain=domain, category=BusinessCategory.OTHER, is_relevant=True,
    )


def _normalize_confidence(value) -> float:
    try:
        c = float(value)
    except (TypeError, ValueError):
        return 0.5
    if c > 1:
        c = c / 100.0
    return max(0.0, min(1.0, c))


def _parse_domain(value) -> Domain:
    try:
        return Domain(str(value).strip().lower())
    except ValueError:
        return Domain.ADMIN


def _parse_category(value) -> BusinessCategory:
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
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def classify_domain(text: str) -> Domain:
    """
    도메인(admin/technical) 판단만 하는 독립 호출. 실패 시 키워드 기반 추정으로 폴백.

    파싱 시 "전체 응답이 순수 JSON이어야 한다"는 엄격한 요구를 버리고, 응답 어디에
    있든 "domain": "admin" 또는 "domain": "technical" 패턴을 정규식으로 찾는다.
    실제로 겪은 문제: 이 프롬프트처럼 짧고 단일 판단만 요구하는 경우, CLOVA가
    "JSON만 출력하라"는 지시를 자주 무시하고 설명글부터 쓴 뒤(때로는 그 끝에
    JSON을 붙이고, 때로는 끝까지 설명만 하다 끝남) 응답한다. json.loads()는
    설명글이 앞에 붙으면 무조건 실패하므로, 그 결과 거의 매번 파싱 실패 →
    좁은 키워드 목록 폴백으로 떨어져 도메인 분류 정확도가 크게 하락하는
    사고가 있었다(DECISION_LOG 참고). 정규식으로 "설명글 속에 파묻힌 판단"도
    끝까지 찾아내도록 완화해 이 문제를 근본적으로 방어한다.
    """
    raw = _call_with_retry(settings.classifier_model, DOMAIN_CLASSIFIER_SYSTEM, text, max_tokens=300)
    if raw is None:
        print(f"[WARN] classify_domain: LLM 응답 없음, 키워드 폴백 사용: {text[:30]!r}")
        return _guess_domain(text)

    # 1차: 응답 전체가 순수 JSON인 경우 (프롬프트를 잘 지킨 경우, 가장 신뢰도 높음)
    try:
        data = json.loads(_strip_code_fence(raw))
        return _parse_domain(data.get("domain", "admin"))
    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    # 2차: 설명글 속에 "domain": "admin"/"technical" 패턴이 섞여 있는 경우 정규식으로 추출
    match = re.search(r'"domain"\s*:\s*"(admin|technical)"', raw)
    if match:
        print(f"[INFO] classify_domain: 순수 JSON은 아니었으나 정규식으로 도메인 추출 성공: {text[:30]!r}")
        return Domain(match.group(1))

    # 3차: 그것도 없으면(설명만 하다 끝난 경우) 응답 텍스트에서 "admin"/"technical" 단어 자체를 찾아본다
    #      (마지막에 언급된 쪽을 최종 결론으로 간주 — 보통 결론을 맨 끝에 말하는 경향이 있음)
    admin_pos = raw.rfind("admin")
    tech_pos = raw.rfind("technical")
    if admin_pos == -1 and tech_pos == -1:
        print(f"[WARN] classify_domain: JSON도 단어도 못 찾음(raw={raw[:80]!r}), 키워드 폴백 사용: {text[:30]!r}")
        return _guess_domain(text)
    print(f"[INFO] classify_domain: JSON 없었으나 응답 속 단어로 추출: {text[:30]!r}")
    return Domain.ADMIN if admin_pos > tech_pos else Domain.TECHNICAL


def classify(text: str) -> Classification:
    domain = classify_domain(text)

    raw = _call_with_retry(settings.classifier_model, CLASSIFIER_SYSTEM, text, max_tokens=256)

    if raw is None:
        fb = _fallback(text)
        return fb.model_copy(update={"domain": domain})

    try:
        data = json.loads(_strip_code_fence(raw))
        return Classification(
            type=InquiryType(data["type"]),
            key_request=data.get("key_request", text[:50]),
            confidence=_normalize_confidence(data.get("confidence", 0.5)),
            domain=domain,
            category=_parse_category(data.get("category", "기타")),
            is_relevant=bool(data.get("is_relevant", True)),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[WARN] classify: JSON 파싱 실패({type(e).__name__}: {e}), 원본 응답={raw[:200]!r}")
        fb = _fallback(text)
        return fb.model_copy(update={"domain": domain})