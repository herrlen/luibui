"""Liveness and readiness. ``/health`` returns 200 only if the database answers."""

import logging
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from luibui_api.db import get_engine
from luibui_scan import __version__ as engine_version

log = logging.getLogger(__name__)
router = APIRouter()


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    engine_version: str


def database_ok() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        # The exception text may contain the connection string; log only the type.
        log.warning("health: database unavailable", exc_info=False)
        return False
    return True


@router.get("/health", response_model=Health)
def health(response: Response) -> Health:
    if database_ok():
        return Health(status="ok", database="ok", engine_version=engine_version)
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(status="degraded", database="unavailable", engine_version=engine_version)
