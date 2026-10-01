"""FastAPI application. No debug pages, no docs UI in production."""

from fastapi import FastAPI

from luibui_api import errors
from luibui_api.routes import (
    auth,
    befunde,
    guthaben,
    health,
    kontakt,
    konto,
    projects,
    quickscans,
    scans,
    teilen,
    tokens,
)
from luibui_api.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
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
    app.include_router(quickscans.router)
    app.include_router(kontakt.router)
    app.include_router(guthaben.router)
    app.include_router(konto.router)
    app.include_router(teilen.router)
    app.include_router(befunde.router)
    return app
