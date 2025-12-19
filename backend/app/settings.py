from pydantic import BaseModel
import os

class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "dev")  # dev|staging|prod
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    CHROMA_URL: str = os.getenv("CHROMA_URL", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
