import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.db.models_imports  # noqa

from app.modules.users.models import User
from app.auth.passwords import hash_password


def log(msg):
    print(f"✓ {msg}")


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no encontrada. Ejecuta dentro del contenedor backend."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)

    session = Session()

    email = "kepler@dev.com"

    existing = session.scalar(select(User).where(User.email == email))

    if existing:
        log(f"platform_admin ya existe: {email}")
        return

    user = User(
        email=email,
        password_hash=hash_password("Admin123!"),
        role="platform_admin",
        school_id=None,
        is_active=True,
        reset_token_version=0,
    )

    session.add(user)
    session.commit()

    log("platform_admin creado")
    print("")
    print("Credenciales:")
    print(f"email: {email}")
    print("password: Admin123!")


if __name__ == "__main__":
    main()
