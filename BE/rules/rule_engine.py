"""
2단계: 룰 적용.
분류된 업무영역(category)을 실제 협회 조직도의 부서로 매핑한다.
(기존에는 type(행위) 기준으로 매핑해 대부분 '민원안내팀'으로 쏠렸음.
 조직도 확인 후 category(업무영역) 기준으로 바꿔 부서와 1:1 매칭되게 함.)

우선순위는 여전히 type + 본문의 긴급 키워드로 판단 (부서와는 별개 축).
"""
from BE.core.schemas import Classification, RuleResult, InquiryType, BusinessCategory

# 업무영역(category) → 실제 담당부서 (조직도 기준, 1:1 매칭)
_DEPT_MAP: dict[BusinessCategory, str] = {
    BusinessCategory.SAFETY_MANAGER: "안전관리지원팀",
    BusinessCategory.DESIGN_SUPERVISION: "설계감리지원팀",
    BusinessCategory.CAREER_MEMBERSHIP: "회원관리팀",
    BusinessCategory.MUTUAL_AID: "공제운영팀",
    BusinessCategory.EDUCATION: "교육원(교육운영팀)",
    BusinessCategory.CONSORTIUM: "교육원(인적자원개발팀)",
    BusinessCategory.WEBSITE_IT: "정보전략실",
    BusinessCategory.TECHNICAL_SUPPORT: "연구원",
    # OTHER 는 아래 apply_rules 에서 별도 처리 (경영지원팀 + 불확실 플래그)
}
_FALLBACK_DEPARTMENT = "경영지원팀"
_FALLBACK_NOTE = "업무영역을 명확히 판단하지 못해 경영지원팀으로 임시 배정되었습니다. 내용을 확인해 알맞은 부서로 재배정해 주세요."

# 유형(type) → 기본 우선순위 (부서와는 무관한 축)
_PRIORITY_MAP: dict[InquiryType, str] = {
    InquiryType.URGENT: "긴급",
    InquiryType.CANCEL_REFUND: "높음",
    InquiryType.ERROR: "높음",
}
_DEFAULT_PRIORITY = "보통"

# 본문에 이게 있으면 유형과 무관하게 우선순위를 끌어올린다
_URGENT_KEYWORDS = ["마감", "당장", "즉시", "급합니다", "오늘까지", "불만", "항의", "피해"]


def apply_rules(text: str, cls: Classification) -> RuleResult:
    priority = _PRIORITY_MAP.get(cls.type, _DEFAULT_PRIORITY)
    if any(k in text for k in _URGENT_KEYWORDS) and priority != "긴급":
        priority = "긴급"

    if cls.category == BusinessCategory.OTHER:
        return RuleResult(
            priority=priority,
            department=_FALLBACK_DEPARTMENT,
            department_certain=False,
            department_note=_FALLBACK_NOTE,
        )

    department = _DEPT_MAP.get(cls.category, _FALLBACK_DEPARTMENT)
    return RuleResult(priority=priority, department=department, department_certain=True)