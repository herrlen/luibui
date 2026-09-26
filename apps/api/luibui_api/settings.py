"""Configuration from environment variables only. Secrets are SecretStr so they never show up in
repr(), logs or error pages."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    luibui_env: Environment = Environment.DEV
    database_url: SecretStr
    """postgresql+psycopg://user:password@host:5432/db"""
    db_pool_size: int = 5
    health_db_timeout_seconds: float = 2.0
    master_key: SecretStr | None = None
    """32 random bytes, base64. Encrypts the per-project data keys (S2-7). Never rotate by
    replacing it: every stored file would become unreadable."""
    storage_root: Path = Path("/projects")

    @property
    def is_prod(self) -> bool:
        return self.luibui_env is Environment.PROD


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
