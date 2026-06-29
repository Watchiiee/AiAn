"""
2단계: 룰 적용.
분류 유형을 받아 우선순위와 담당부서를 확정한다.
계획서 6번 표의 '담당(예시)'을 그대로 옮긴 매핑이다.
하이브리드 룰: 유형 기반 매핑 + 긴급 키워드가 있으면 우선순위 승격.
"""
from BE.core.schemas import Classification, RuleResult, InquiryType

# 유형 → (우선순위, 담당부서)
_DEPT_MAP = {
    InquiryType.CAREER_CERT:  ("보통", "경력관리팀"),
    InquiryType.APPLY:        ("보통", "행정팀"),
    InquiryType.CHANGE:       ("보통", "고객지원팀"),
    InquiryType.CANCEL_REFUND:("높음", "고객지원팀"),
    InquiryType.ERROR:        ("높음", "IT지원팀"),
    InquiryType.GENERAL:      ("보통", "민원안내팀"),
    InquiryType.URGENT:       ("긴급", "긴급대응팀"),
    InquiryType.UNKNOWN:      ("보통", "민원안내팀"),
}

# 본문에 이게 있으면 유형과 무관하게 우선순위를 끌어올린다
_URGENT_KEYWORDS = ["마감", "당장", "즉시", "급합니다", "오늘까지"]


def apply_rules(text: str, cls: Classification) -> RuleResult:
    priority, dept = _DEPT_MAP.get(cls.type, ("보통", "민원안내팀"))

    # 긴급 키워드 승격: 긴급문의가 아니어도 본문이 급하면 우선순위 상향
    if any(k in text for k in _URGENT_KEYWORDS) and priority != "긴급":
        priority = "긴급"

    return RuleResult(priority=priority, department=dept)