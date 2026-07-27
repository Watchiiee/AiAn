"""
담당자 코파일럿 엔드포인트의 부서 권한체크 회귀테스트(Y-7에서 검증했던
로직). LLM 실제 호출 없이(요청이 권한 단계에서 막히므로 도달 안 함) 순수
권한 로직만 검증한다.
"""
import pytest
from fastapi import HTTPException

from BE.api.inquiry import inquiry_copilot
from BE.core.schemas import CopilotRequest


def test_other_department_staff_forbidden(db_session, make_inquiry):
    record = make_inquiry(department="연구원")
    other_dept_user = {"role": "staff", "department": "회원관리팀"}

    with pytest.raises(HTTPException) as exc_info:
        inquiry_copilot(
            inquiry_id=record.id,
            req=CopilotRequest(question="왜 이 문서를 선택했어?"),
            db=db_session,
            user=other_dept_user,
        )

    assert exc_info.value.status_code == 403


def test_staff_with_no_department_forbidden(db_session, make_inquiry):
    """부서가 아예 지정 안 된 staff도(department=None) 접근 못 해야 한다 -
    RBAC 테스트와 동일한 종류의 안전장치."""
    record = make_inquiry(department="연구원")
    no_dept_user = {"role": "staff", "department": None}

    with pytest.raises(HTTPException) as exc_info:
        inquiry_copilot(
            inquiry_id=record.id,
            req=CopilotRequest(question="왜 이 문서를 선택했어?"),
            db=db_session,
            user=no_dept_user,
        )

    assert exc_info.value.status_code == 403


def test_inquiry_not_found_returns_404(db_session):
    user = {"role": "master"}

    with pytest.raises(HTTPException) as exc_info:
        inquiry_copilot(
            inquiry_id=99999,
            req=CopilotRequest(question="아무 질문"),
            db=db_session,
            user=user,
        )

    assert exc_info.value.status_code == 404