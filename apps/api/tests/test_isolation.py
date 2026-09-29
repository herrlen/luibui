"""DoD Sprint 2 and CLAUDE.md rule 9: user B reaches nothing of user A, on every route.

The routes come from the app's OpenAPI schema, so a new route with a resource ID is covered
automatically. A path parameter this test does not know fails the test until it is added below.
"""

from typing import Any

from .conftest import Api
from .test_guthaben import FakePayPal, api_bezahlt, bestaetigt, einzel, kaufen, pp  # noqa: F401
from .test_scans import project, upload_zip

ERLAUBT = {404}
"""Foreign resources look like missing ones (CLAUDE.md rule 9)."""
OEFFENTLICH = {"/api/v1/geteilt/{token}"}
"""Public by design: the random link token itself is the permission (S2-12, test_teilen.py)."""


def _ids_von_a(a: Any, paypal: FakePayPal) -> dict[str, list[str]]:
    pid = project(a)
    scan = upload_zip(a, pid).json()["id"]
    einzelpruefung = einzel(a).json()["id"]
    token = a.post("/api/v1/tokens", json={"name": "ci"}).json()["id"]
    kaufen(a, paypal)
    (beleg,) = a.get("/api/v1/guthaben").json()["kaeufe"]
    return {
        "project_id": [pid],
        "scan_id": [scan, einzelpruefung],
        "token_id": [token],
        "payment_id": [beleg["id"]],
    }


def test_user_b_reaches_nothing_of_user_a_on_any_route(
    api_bezahlt: Api,  # noqa: F811
    pp: FakePayPal,  # noqa: F811
) -> None:
    a = bestaetigt(api_bezahlt, "a@luibui.example")
    b = bestaetigt(api_bezahlt, "b@luibui.example")
    ids = _ids_von_a(a, pp)
    routen = b.get("/openapi.json").json()["paths"]
    geprueft = []
    for pfad, operationen in routen.items():
        params = [s[1:-1] for s in pfad.split("/") if s.startswith("{")]
        if not params or pfad in OEFFENTLICH:
            continue
        unbekannt = [p for p in params if p not in ids]
        assert not unbekannt, f"{pfad}: Parameter {unbekannt} im Isolationstest ergänzen"
        for wert in ids[params[0]]:
            url = pfad.replace("{" + params[0] + "}", wert)
            for methode in operationen:
                antwort = b.request(methode.upper(), url)
                geprueft.append(f"{methode.upper()} {pfad}")
                assert antwort.status_code in ERLAUBT, (methode, url, antwort.status_code)
                assert wert not in antwort.text
    # A's data is still there: B's requests changed nothing.
    assert a.get(f"/api/v1/projects/{ids['project_id'][0]}").status_code == 200
    assert a.get(f"/api/v1/scans/{ids['scan_id'][0]}").status_code == 200
    assert len(geprueft) >= 11
