from __future__ import annotations
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────
    APP_NAME: str = "Sentinel"
    APP_ENV: str = "development"
    DEBUG: bool = True
    DRY_RUN: bool = True

    # ── Database (IMPORTANT FIX) ─────────────────────────────
    # MySQL
    DATABASE_URL: str = "postgresql://postgres:1234@127.0.0.1:5432/sentinel"
    ASYNC_DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@127.0.0.1:5432/sentinel"

    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Twilio ─────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ── Firebase ───────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"

    # ── AWS S3 ─────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_EVIDENCE_BUCKET: str = "sentinel-evidence"

    # ── Escalation ─────────────────────────────────────────
    ESCALATION_SLA_SECONDS: int = 60

    # ── CORS ───────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ── Connection Pool ────────────────────────────────────
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


# Singleton
settings = Settings()