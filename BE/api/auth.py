"""
인증 라우터: 회원가입 / 로그인.
로그인 성공 시 JWT 액세스 토큰을 발급한다 (세션을 DB에 두지 않는 무상태 방식).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from BE.core.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from BE.core.auth import hash_password, verify_password, create_access_token
from BE.db.database import get_db
from BE.db.models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """회원가입. 이메일 중복 시 409."""
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 이메일입니다.")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=UserRole(req.role.value),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """로그인. 성공하면 JWT 액세스 토큰을 발급한다."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        # 이메일/비밀번호 중 뭐가 틀렸는지 알려주지 않는다 (계정 존재 여부 노출 방지)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value)
    return TokenResponse(access_token=token, role=user.role.value)