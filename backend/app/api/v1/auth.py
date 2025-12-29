from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.db import get_db
from app.modules.users.models import User
from app.auth.schemas import LoginRequest, TokenResponse, MeResponse
from app.auth.passwords import verify_password
from app.auth.jwt import create_access_token
from app.auth.deps import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        school_id=str(user.school_id) if user.school_id else None,
    )
    return TokenResponse(access_token=token)

@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        school_id=str(current_user.school_id) if current_user.school_id else None,
    )
