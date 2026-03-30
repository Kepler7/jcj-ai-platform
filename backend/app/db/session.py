from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def normalize_database_url(url: str | None) -> str | None:
    if not url:
        return url

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    normalized = normalize_database_url(url)
    if not normalized:
        raise RuntimeError("DATABASE_URL is not configured")
    return normalized


@lru_cache
def get_engine():
    return create_engine(get_database_url(), future=True)


@lru_cache
def get_session_factory():
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        future=True,
    )


def get_db_session() -> Session:
    return get_session_factory()()
