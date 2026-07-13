"""
2단계: 룰 적용.
분류된 업무영역(category)을 실제 협회 조직도의 부서로 매핑한다.

우선순위:
  - type(행위) 기준 기본값만 여기서 정한다 (오류/장애·취소환불은 '높음' 등).
  - "긴급" 최종 판정은 여기서 안 한다 — 키워드 매칭은 "긴급! 사랑해요" 같은
    거짓 양성(false positive) 위험이 있어 제거했다. 대신 파이프라인의
    check_urgency 노드가 문맥 기반 LLM 판단 + 근거(urgent_reason)로 확정하고,
    그 근거가 있을 때만 priority를 '긴급'으로 덮어쓴다 (BE/api/pipeline.py 참고).
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
}
_FALLBACK_DEPARTMENT = "경영지원팀"
_FALLBACK_NOTE = "업무영역을 명확히 판단하지 못해 경영지원팀으로 임시 배정되었습니다. 내용을 확인해 알맞은 부서로 재배정해 주세요."

# 유형(type) → 기본 우선순위 (부서와는 무관한 축, '긴급'은 여기서 안 매김)
_PRIORITY_MAP: dict[InquiryType, str] = {
    InquiryType.CANCEL_REFUND: "높음",
    InquiryType.ERROR: "높음",
}
_DEFAULT_PRIORITY = "보통"


def apply_rules(text: str, cls: Classification) -> RuleResult:
    priority = _PRIORITY_MAP.get(cls.type, _DEFAULT_PRIORITY)

    if cls.category == BusinessCategory.OTHER:
        return RuleResult(
            priority=priority,
            department=_FALLBACK_DEPARTMENT,
            department_certain=False,
            department_note=_FALLBACK_NOTE,
        )

    department = _DEPT_MAP.get(cls.category, _FALLBACK_DEPARTMENT)
    return RuleResult(priority=priority, department=department, department_certain=True)