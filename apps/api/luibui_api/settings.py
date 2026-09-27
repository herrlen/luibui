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
    scratch_root: Path = Path("/scratch")
    """Shared with the worker: uploads are unpacked to ``<scratch_root>/<job-id>`` for the scan."""
    upload_max_bytes: int = 60 * 1024 * 1024
    """Request body limit for uploads (ZIP 50 MB or selection 50 MB plus multipart overhead)."""
    account_quota_bytes: int = 500 * 1024 * 1024
    versions_per_project: int = 10
    quickscans_per_ip_and_day: int = 3
    quickscan_queue_max: int = 20
    """Waiting quick scans; beyond that new ones get 503 instead of piling up (threat model T20)."""

    annahme_offen: bool = False
    """Registration, uploads and quick scans. Stays off in production until the worker has no
    internet access and client IPs behind the proxy are trusted (docs/log.md, 2026-09-27)."""
    app_origin: str = "https://app.luibui.com"
    """The only origin whose cookie-authenticated, state-changing requests are accepted (CSRF)."""
    bearer_only_hosts: frozenset[str] = frozenset({"api.luibui.com"})
    """Hosts that accept only Bearer tokens; session cookies are ignored there (rule 11)."""
    session_days: int = 14
    session_cookie_secure: bool = True
    login_max_attempts: int = 10
    """Failed logins per e-mail address and per client within ``login_window_seconds``."""
    login_window_seconds: int = 900

    @property
    def is_prod(self) -> bool:
        return self.luibui_env is Environment.PROD


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
