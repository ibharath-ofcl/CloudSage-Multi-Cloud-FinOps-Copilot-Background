"""
CloudSage Core Configuration.
Manages application settings, database connection URLs, and runtime parameters.
"""

from typing import List
from pydantic import model_validator
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
    VERSION: str = "0.15.0"
    APP_VERSION: str = "0.15.0"

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

    # Security & RBAC Hardening
    SECRET_KEY: str = "development-secret-key-change-in-production-stage"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "cloudsage-auth"
    JWT_AUDIENCE: str = "cloudsage-api"
    ALLOW_DEV_AUTH_HEADERS: bool = True  # Allowed only when ENVIRONMENT=="development"
    TRUSTED_PROXY_IPS: List[str] = ["127.0.0.1", "::1"]
    PASSWORD_MIN_LENGTH: int = 12
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = 60
    REQUIRE_DUAL_APPROVAL_FOR_SUPER_ADMIN: bool = True

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

    # Observability & Production Runtime
    METRICS_ENABLED: bool = True
    METRICS_PATH: str = "/metrics"
    LOG_FORMAT: str = "json"  # json or text
    LOG_LEVEL: str = "INFO"
    REQUEST_ID_HEADER: str = "X-Request-ID"
    GUNICORN_WORKERS: int = 4
    GUNICORN_TIMEOUT: int = 120
    HEALTHCHECK_TIMEOUT_SECONDS: float = 3.0

    # Notifications & Alerts
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = False
    EMAIL_FROM: str = "alerts@cloudsage.internal"
    WEBHOOK_TIMEOUT_SECONDS: int = 10
    WEBHOOK_MAX_RETRIES: int = 3
    NOTIFICATION_SAFE_LOCAL_MODE: bool = True

    @model_validator(mode="after")
    def validate_production_security(self):
        """Enforces security hardening rules when running in production environment."""
        env = (self.ENVIRONMENT or "").strip().lower()
        if env == "production":
            if self.SECRET_KEY == "development-secret-key-change-in-production-stage" or len(self.SECRET_KEY) < 32:
                raise ValueError("Production environment requires a secure, non-default SECRET_KEY with at least 32 characters.")
            if self.ALLOW_DEV_AUTH_HEADERS:
                raise ValueError("ALLOW_DEV_AUTH_HEADERS must be False in production environment.")
            if self.POSTGRES_PASSWORD == "postgres" and not self.DATABASE_URL:
                raise ValueError("Production environment cannot use default PostgreSQL password ('postgres').")
        return self

    def is_production(self) -> bool:
        return (self.ENVIRONMENT or "").strip().lower() == "production"

    def is_development(self) -> bool:
        return (self.ENVIRONMENT or "").strip().lower() == "development"

    def is_testing(self) -> bool:
        return (self.ENVIRONMENT or "").strip().lower() in ("test", "testing")

    def get_async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def get_sync_database_url(self) -> str:
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
