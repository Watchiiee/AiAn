"""
FastAPI 라우터에서 쓰는 인증 의존성.

권한은 계층형이다: master ⊃ staff ⊃ general
  - general: 로그인만 하면 됨 (get_current_user)
  - staff:   담당자 전용 (require_staff) — master도 통과됨 (상위 권한 포함)
  - master:  최고관리자 전용 (require_master) — master만 통과

사용 예:
    @router.get("/staff-only")
    def handler(user: dict = Depends(require_staff)):
        ...  # staff 또는 master 만 접근 가능

    @router.patch("/master-only")
    def handler(user: dict = Depends(require_master)):
        ...  # master 만 접근 가능
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from BE.core.auth import decode_access_token

_bearer_scheme = HTTPBearer()

_STAFF_OR_ABOVE = {"staff", "master"}   # require_staff 를 통과할 수 있는 역할들
_MASTER_ONLY = {"master"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """Authorization: Bearer <token> 헤더를 검증하고 payload를 돌려준다."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다.",
        )
    return payload  # {"sub": user_id, "email": ..., "role": ..., "exp": ...}


def require_staff(user: dict = Depends(get_current_user)) -> dict:
    """담당자 이상(staff, master) 전용. 일반 사용자면 403."""
    if user.get("role") not in _STAFF_OR_ABOVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="담당자만 접근할 수 있습니다.",
        )
    return user


def require_master(user: dict = Depends(get_current_user)) -> dict:
    """최고관리자(master) 전용. staff·general 이면 403."""
    if user.get("role") not in _MASTER_ONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="최고관리자만 접근할 수 있습니다.",
        )
    return user