import bcrypt

def hash_password(password: str) -> str:
    # bcrypt requiere bytes
    pw_bytes = password.encode("utf-8")

    # Genera salt y hash
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12))

    # Guardamos como string
    return hashed.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode("utf-8")
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hash_bytes)
