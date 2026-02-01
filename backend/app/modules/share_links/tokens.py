from __future__ import annotations

import hashlib
import secrets


def generate_raw_token(num_bytes: int = 32) -> str:
    """
    Token “crudo” para compartir. Se entrega solo una vez al crear el link.
    32 bytes => 43 chars aprox en base64url.
    """
    return secrets.token_urlsafe(num_bytes)


def sha256_hex(value: str) -> str:
    """
    Devuelve sha256 en hex (64 chars). Esto es lo que guardamos en DB como token_hash.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
