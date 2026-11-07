"""
CloudSage Core Configuration.
Manages application settings, database connection URLs, and runtime parameters.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "CloudSage - Multi-Cloud FinOps Copilot"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # PostgreSQL Connection Parameters
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "cloudsage"
    POSTGRES_PORT: int = 5432

    # Async & Sync Database URLs
    # Default SQLite fallback for isolated lightweight tests if PostgreSQL is unavailable
    DATABASE_URL: str = ""
    SYNC_DATABASE_URL: str = ""

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Security
    SECRET_KEY: str = "development-secret-key-change-in-production-stage"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI FinOps Copilot
    COPILOT_ENABLED: bool = True
    COPILOT_PROVIDER: str = "auto"  # auto, openai, anthropic, fallback
    COPILOT_MODEL_NAME: str = "gpt-4o-mini"
    COPILOT_API_KEY: str = ""
    COPILOT_API_ENDPOINT: str = ""
    COPILOT_REQUEST_TIMEOUT_SECONDS: int = 30
    COPILOT_MAX_TOKENS: int = 1500
    COPILOT_TEMPERATURE: float = 0.0
    COPILOT_RATE_LIMIT_PER_MINUTE: int = 60
    COPILOT_DEMO_MODE: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    def get_async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def get_sync_database_url(self) -> str:
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
