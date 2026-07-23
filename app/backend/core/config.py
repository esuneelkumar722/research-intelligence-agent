
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", pattern="^(development|staging|production)$")
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3001"])

    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_deployment: str = "gpt-5-mini"
    azure_openai_api_key: str = ""  # local dev only; leave empty in production (Managed Identity)

    azure_key_vault_url: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "research_agent"
    postgres_user: str = "research_user"
    postgres_password: str = ""

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    redis_url: str = ""  # empty = in-memory rate limiting (not suitable for multi-replica)
    cache_ttl_seconds: int = 3600

    tavily_api_key: str = ""

    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    applicationinsights_connection_string: str = ""

    azure_content_safety_endpoint: str = ""
    azure_content_safety_key: str = ""

    azure_auth_tenant_id: str = ""
    azure_auth_client_id: str = ""
    azure_auth_audience: str = ""

    rate_limit_per_minute: int = 20
    max_tokens_per_request: int = 10000

    enable_auth: bool = False
    enable_cache: bool = True
    enable_safety: bool = True
    enable_langfuse: bool = True

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
