"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = ""

    DATABASE_URL: str = "postgresql+asyncpg://neuro:neuro_dev_password@postgres:5432/neuro"
    REDIS_URL: str = "redis://redis:6379/0"

    GEMINI_API_KEY: str = ""
    GEMINI_GENERATION_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    SENTRY_DSN: str = ""
    ADMIN_API_KEY: str = ""

    RATE_LIMIT_RPM: int = 1000
    RATE_LIMIT_MESSAGES_PM: int = 100
    RATE_LIMIT_CHAT_STUDENT_PM: int = 30
    RATE_LIMIT_INGEST_PM: int = 10

    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.65

    GEMINI_TIMEOUT: int = 45

    SESSION_CONTENT_MAX_LENGTH: int = 100000
    SESSION_CONTENT_MIN_LENGTH: int = 50
    SESSION_AUTO_EXPIRE_INACTIVE_HOURS: int = 24
    SESSION_AUTO_EXPIRE_NEVER_USED_HOURS: int = 2
    EMBEDDING_CACHE_TTL_DAYS: int = 30
    EMBEDDING_CACHE_MAX_ROWS: int = 100000


settings = Settings()
