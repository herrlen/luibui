"""One error format for the whole API (ENTWICKLERREGELN C):

    {"detail": {"code": "<stable, machine-readable>", "text": "<German, may change>", ...}}

Clients branch on ``code``, never on ``text``. Validation errors name the fields but never echo the
submitted values (FastAPI's default would send a wrong password straight back).
"""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

DEFAULT_CODES = {
    400: "ungueltige_anfrage",
    401: "nicht_angemeldet",
    403: "verboten",
    404: "nicht_gefunden",
    405: "methode_nicht_erlaubt",
    409: "konflikt",
    411: "laenge_fehlt",
    413: "zu_gross",
    422: "ungueltige_eingabe",
    429: "zu_viele_anfragen",
    503: "nicht_verfuegbar",
}


def fehler(status_code: int, code: str, text: str, **extra: Any) -> HTTPException:
    """Build an HTTPException in the API's error format."""
    return HTTPException(status_code, {"code": code, "text": text, **extra})


def _body(status_code: int, detail: Any) -> dict[str, Any]:
    if isinstance(detail, dict) and "code" in detail:
        return {"detail": detail}
    text = detail if isinstance(detail, str) else "Fehler"
    return {"detail": {"code": DEFAULT_CODES.get(status_code, "fehler"), "text": text}}


def install(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            _body(exc.status_code, exc.detail), status_code=exc.status_code, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        felder = sorted(
            {".".join(str(p) for p in e.get("loc", ())[1:]) or "anfrage" for e in exc.errors()}
        )
        body = {
            "detail": {
                "code": "ungueltige_eingabe",
                "text": "Die Eingabe ist unvollständig oder ungültig.",
                "felder": felder,
            }
        }
        return JSONResponse(body, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
