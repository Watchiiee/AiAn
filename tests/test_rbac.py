"""
부서 필터링(RBAC) 회귀테스트.

W절에서 실제로 겪었던 버그: User.department가 없어서 모든 staff가 전체
검토대기 큐를 보던 문제. FastAPI 라우트 함수(list_pending_inquiries)를
HTTP 계층 없이 직접 호출해 그 비즈니스 로직(마스터/스태프 분기, 미배정
staff는 빈 목록)을 검증한다 - 이 로직은 crud가 아니라 API 함수 안에
있으므로(BE/api/inquiry.py), crud만 테스트하면 이 버그를 못 잡는다.
"""
from BE.api.inquiry import list_pending_inquiries


def test_master_sees_all_departments(db_session, make_inquiry):
    make_inquiry(department="연구원")
    make_inquiry(department="회원관리팀")
    make_inquiry(department="공제운영팀")

    result = list_pending_inquiries(db=db_session, user={"role": "master"})

    assert len(result) == 3


def test_staff_sees_only_own_department(db_session, make_inquiry):
    make_inquiry(department="연구원", original_text="연구원 문의 1")
    make_inquiry(department="연구원", original_text="연구원 문의 2")
    make_inquiry(department="회원관리팀", original_text="회원관리팀 문의")

    result = list_pending_inquiries(db=db_session, user={"role": "staff", "department": "연구원"})

    assert len(result) == 2
    assert all(r.department == "연구원" for r in result)


def test_staff_with_no_department_sees_empty_list(db_session, make_inquiry):
    """W절 버그의 핵심 - department가 없는(None) staff는 전체가 아니라
    빈 목록을 봐야 한다. 이게 예전엔 '필터링 조건 자체가 안 걸려서' 전체가
    보이는 버그였다."""
    make_inquiry(department="연구원")
    make_inquiry(department="회원관리팀")

    result = list_pending_inquiries(db=db_session, user={"role": "staff", "department": None})

    assert result == []


def test_staff_department_with_no_matching_inquiries(db_session, make_inquiry):
    """자기 부서로 배정된 문의가 하나도 없으면, 다른 부서 문의가 새어
    보이지 않고 정확히 빈 목록이어야 한다."""
    make_inquiry(department="회원관리팀")
    make_inquiry(department="공제운영팀")

    result = list_pending_inquiries(db=db_session, user={"role": "staff", "department": "연구원"})

    assert result == []