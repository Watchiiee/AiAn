from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from BE.core.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from BE.core.auth import hash_password, verify_password, create_access_token
from BE.db.database import get_db
from BE.db.models import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 가입된 이메일입니다.")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=UserRole.GENERAL,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token(user_id=user.id, email=user.email, role=user.role.value, department=user.department)
    return TokenResponse(access_token=token, role=user.role.value, department=user.department)