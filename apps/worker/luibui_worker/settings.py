"""Worker configuration from environment variables."""

import socket
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_JOB_TIMEOUT_SECONDS = 300
"""Hard upper limit per job (Konzept §8: timeout 5 min), whatever the job row says."""


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    database_url: SecretStr
    scratch_root: Path = Path("/scratch")
    worker_id: str = Field(default_factory=socket.gethostname, max_length=100)
    poll_interval_seconds: float = 2.0
    kill_grace_seconds: float = 5.0
    stale_grace_seconds: int = 60
    max_result_bytes: int = 20 * 1024 * 1024
    osv_db: Path = Path("/rules/osv")
    osv_max_age_hours: float = 24.0
    osv_refresh: bool = True


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()  # values come from the environment
