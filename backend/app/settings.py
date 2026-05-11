from pydantic import BaseModel
import os


class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "dev")  # dev|staging|prod
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CHROMA_URL: str = os.getenv("CHROMA_URL", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PUBLIC_APP_URL: str = os.getenv("PUBLIC_APP_URL", "http://localhost:5173")
    IHUI_ENGINE_VERSION: str = os.getenv("IHUI_ENGINE_VERSION", "2")
    IHUI3_SHEET_CSV_URL: str = os.getenv("IHUI3_SHEET_CSV_URL", "")
    IHUI3_KNOWLEDGE_SOURCE: str | None = os.getenv(
        "IHUI3_KNOWLEDGE_SOURCE", "/app/data/ihui3/ihui3_knowledge.normalized.jsonl"
    )
    IHUI3_REVIEW_THRESHOLD: float = float(os.getenv("IHUI3_REVIEW_THRESHOLD", "0.70"))
    IHUI3_DICTIONARY_CSV_URL: str = os.getenv("IHUI3_DICTIONARY_CSV_URL", "")

    IHUI3_DICTIONARY_SOURCE: str = os.getenv(
        "IHUI3_DICTIONARY_SOURCE",
        "/app/data/ihui3/ihui3_dictionary.normalized.jsonl",
    )


settings = Settings()
