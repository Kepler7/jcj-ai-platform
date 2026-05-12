# app/auth/jwt.py
import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))


def create_access_token(*, user_id: str, role: str, school_id: str | None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role,
        "school_id": school_id,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_password_reset_token(*, user_id: str, email: str, ver: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "pwd_reset",
        "ver": ver,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise ValueError("Invalid token")


def decode_password_reset_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("purpose") != "pwd_reset":
        raise ValueError("Invalid token purpose")
    if "ver" not in payload:
        raise ValueError("Invalid token payload")
    return payload
