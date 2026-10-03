"""FastAPI application. No debug pages, no docs UI in production."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from luibui_api import errors
from luibui_api.nachpruefung import Nachpruefer
from luibui_api.routes import (
    auth,
    befunde,
    dateien,
    guthaben,
    health,
    kontakt,
    konto,
    namespaces,
    pakete,
    projects,
    quickscans,
    scans,
    teilen,
    tokens,
    verlauf,
    webhooks,
)
from luibui_api.settings import Environment, get_settings


@asynccontextmanager
async def _lebenszeit(app: FastAPI) -> AsyncIterator[None]:
    """Starts the nightly re-check thread (S4-7) except in tests."""
    settings = get_settings()
    pruefer = None
    if settings.nachpruefung and settings.luibui_env is not Environment.TEST:
        pruefer = Nachpruefer()
        pruefer.start()
    yield
    if pruefer is not None:
        pruefer.stopp.set()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        lifespan=_lebenszeit,
        title="luibui API",
        debug=False,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
    )
    errors.install(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tokens.router)
    app.include_router(projects.router)
    app.include_router(scans.router)
    app.include_router(befunde.router)
    app.include_router(quickscans.router)
    app.include_router(kontakt.router)
    app.include_router(guthaben.router)
    app.include_router(konto.router)
    app.include_router(teilen.router)
    app.include_router(verlauf.router)
    app.include_router(dateien.router)
    app.include_router(namespaces.router)
    app.include_router(pakete.router)
    app.include_router(webhooks.router)
    return app
