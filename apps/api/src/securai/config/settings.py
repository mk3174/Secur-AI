"""Application configuration (12-factor, env-driven).

Settings are the single source of truth for configuration. Never read
``os.environ`` directly elsewhere in the codebase.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SECURAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SecurAI"
    environment: str = Field(default="local", description="local|staging|production")
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    # Default to a local SQLite file for zero-config dev; use asyncpg in prod.
    database_url: str = "sqlite+aiosqlite:///./securai.db"
    db_echo: bool = False
    auto_create_schema: bool = True  # create_all on startup (dev/MVP); use Alembic in prod

    # --- Security ---
    jwt_secret: str = Field(
        default="dev-insecure-secret-change-me",
        description="HMAC secret for dashboard JWTs. MUST be overridden in production.",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 3600
    api_key_prefix: str = "sk_securai"

    # --- Bootstrap (first-run convenience for MVP) ---
    bootstrap_enabled: bool = True
    bootstrap_admin_email: str = "admin@securai.local"
    bootstrap_admin_password: str = "admin12345"
    bootstrap_org_name: str = "Default Org"
    bootstrap_project_name: str = "default"

    # --- LLM provider (Phase 1: single backend) ---
    # "echo" (mock, no network) or "openai_compatible" (vLLM / OpenAI-compatible)
    default_provider: str = "echo"
    default_model: str = "securai-echo-1"
    provider_base_url: str = "http://localhost:8001/v1"
    provider_api_key: str = ""
    provider_timeout_seconds: float = 60.0

    # --- Rate limiting (Phase 1: simple in-process limiter) ---
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True
    # Store full prompt/response text in request logs (respect retention/privacy in prod).
    log_prompt_content: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
