"""FastAPI application. No debug pages, no docs UI in production."""

from fastapi import FastAPI

from luibui_api.routes import auth, health, tokens
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
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tokens.router)
    return app
