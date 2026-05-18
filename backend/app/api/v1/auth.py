import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.db import get_db
from app.modules.users.models import User

from app.auth.schemas import (
    LoginRequest,
    TokenResponse,
    MeResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)

from app.auth.passwords import verify_password, hash_password
from app.auth.jwt import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
)
from app.auth.deps import get_current_user
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/v1/auth", tags=["auth"])

FRONTEND_RESET_URL = os.getenv(
    "FRONTEND_RESET_URL", "http://localhost:5173/reset-password"
)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Respuesta neutra SIEMPRE (anti-enumeración)
    neutral = ForgotPasswordResponse()

    user = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()
    if not user or not user.is_active:
        return neutral

    # Invalida tokens anteriores: incrementa versión
    user.reset_token_version += 1
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_password_reset_token(
        user_id=str(user.id),
        email=user.email,
        ver=user.reset_token_version,
    )

    reset_link = f"{FRONTEND_RESET_URL}?token={token}"

    try:
        send_password_reset_email(to_email=user.email, reset_link=reset_link)
    except Exception as exc:
        # No rompemos el endpoint de forgot password si falla el proveedor de correo.
        # La respuesta debe seguir siendo neutral para evitar enumeración de usuarios.
        print(f"[AUTH] Failed to send password reset email: {exc}")

    return neutral


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        token_payload = decode_password_reset_token(payload.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )

    user_id = token_payload.get("sub")
    ver = token_payload.get("ver")

    if not user_id or ver is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload"
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )

    # Token debe coincidir con la versión actual
    if user.reset_token_version != int(ver):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used token",
        )

    user.password_hash = hash_password(payload.new_password)

    # 1-time-use: invalida el token inmediatamente después de usarlo
    user.reset_token_version += 1

    db.add(user)
    db.commit()

    return ResetPasswordResponse()
