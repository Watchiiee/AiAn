"""
FastAPI 라우터에서 쓰는 인증 의존성.

사용 예:
    @router.get("/some-protected")
    def handler(user: dict = Depends(get_current_user)):
        ...  # user["role"], user["email"] 등 사용 가능

    @router.get("/staff-only")
    def handler(user: dict = Depends(require_staff)):
        ...  # 담당자(staff)가 아니면 403
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from BE.core.auth import decode_access_token

_bearer_scheme = HTTPBearer()


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
    """담당자(staff) 전용 엔드포인트에 사용. 일반 사용자면 403."""
    if user.get("role") != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="담당자만 접근할 수 있습니다.",
        )
    return user