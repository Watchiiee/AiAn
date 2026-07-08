"""
인증 유틸: 비밀번호 해싱 + JWT 토큰 생성/검증.

- 비밀번호는 bcrypt로 해싱해 저장한다 (평문 저장 금지).
  ※ passlib는 최신 bcrypt(4.x)와 호환성 버그가 있어 bcrypt를 직접 사용한다.
- 인증은 세션(DB) 대신 JWT를 쓴다: 배포 시 백엔드를 오토스케일링할
  계획이라, 서버가 여러 대여도 DB 조회 없이(무상태) 토큰만으로
  검증할 수 있어야 하기 때문이다. (자세한 배경은 결정 로그 참고)
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from BE.core.config import settings


# --- 비밀번호 ---

def hash_password(plain_password: str) -> str:
    """비밀번호를 bcrypt로 해싱한다. bcrypt는 72바이트 제한이 있어 자른다."""
    pw_bytes = plain_password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호가 저장된 해시와 일치하는지 확인한다."""
    pw_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))


# --- JWT ---

def create_access_token(user_id: int, email: str, role: str) -> str:
    """로그인 성공 시 발급하는 JWT. 토큰 자체에 신원·권한을 담는다(무상태)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),   # subject: 사용자 id
        "email": email,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """토큰을 검증하고 payload를 돌려준다. 위조·만료 등 실패 시 None."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None