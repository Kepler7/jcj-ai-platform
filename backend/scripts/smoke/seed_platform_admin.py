import os
import argparse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.db.models_imports  # noqa

from app.modules.users.models import User
from app.auth.passwords import hash_password


def log(msg: str) -> None:
    print(f"✓ {msg}")


def parse_args():
    parser = argparse.ArgumentParser(description="Crea un platform_admin manualmente.")
    parser.add_argument(
        "--email",
        required=True,
        help="Email del platform_admin",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Password en texto plano del platform_admin",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no encontrada. Ejecuta dentro del contenedor backend."
        )

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing = session.scalar(select(User).where(User.email == args.email))

        if existing:
            log(f"platform_admin ya existe: {args.email}")
            return

        user = User(
            email=args.email,
            password_hash=hash_password(args.password),
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
        print(f"email: {args.email}")
        print(f"password: {args.password}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
