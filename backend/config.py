"""Centralised configuration — validated at startup via pydantic-settings.

All environment variables are declared here with types and defaults.
FastAPI app will refuse to start if a required variable is missing.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    groq_api_key: SecretStr = Field(..., description="Groq API key for Llama-3.3-70b")
    google_api_key: SecretStr = Field(..., description="Google AI API key for Gemini 2.5 Flash")

    # ── MCP tokens ───────────────────────────────────────────────────────────
    github_mcp_token: SecretStr = Field(..., description="GitHub personal access token (read-only)")
    slack_mcp_bot_token: SecretStr = Field(..., description="Slack bot token (chat:write, channels:read)")
    salesforce_mcp_client_id: SecretStr = Field(..., description="Salesforce connected app client_id")
    salesforce_mcp_client_secret: SecretStr = Field(..., description="Salesforce connected app client_secret")
    salesforce_mcp_instance_url: str = Field(..., description="e.g. https://yourorg.my.salesforce.com")

    # ── Supabase ──────────────────────────────────────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: SecretStr = Field(..., description="Supabase service_role key (never expose to browser)")
    supabase_anon_key: SecretStr = Field(..., description="Supabase anon key (safe for frontend)")

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    jwt_private_key: SecretStr = Field(..., description="RS256 PEM private key for signing JWTs")
    jwt_public_key: str = Field(..., description="RS256 PEM public key for verifying JWTs")
    jwt_algorithm: str = Field(default="RS256")
    jwt_expire_minutes: int = Field(default=60, ge=5, le=1440)

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="Comma-separated list is parsed automatically by pydantic-settings",
    )

    # ── App behaviour ─────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_iterations: int = Field(default=10, ge=1, le=50)
    hitl_timeout_seconds: int = Field(default=600, ge=30, le=3600)
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # ── Computed helpers ──────────────────────────────────────────────────────
    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> list[str]:
        """Support comma-separated string from env var."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return list(v)  # type: ignore[arg-type]

    @property
    def is_production(self) -> bool:
        """True when running in production."""
        return self.environment == "production"

    @property
    def groq_api_key_str(self) -> str:
        """Unwrapped Groq key for LangChain constructors."""
        return self.groq_api_key.get_secret_value()

    @property
    def google_api_key_str(self) -> str:
        """Unwrapped Google key for LangChain constructors."""
        return self.google_api_key.get_secret_value()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
