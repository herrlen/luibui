"""S3-7: finding status in the developer area and moderation of disputes."""

from typing import Any

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_guthaben import einzel
from .test_scans import project, upload_zip
from .test_uebersicht import _befund, _fertig


def _sql(url: str, sql: str, **params: Any) -> list[Any]:
    engine = create_engine(url)
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        rows = list(result) if result.returns_rows else []
    engine.dispose()
    return rows


def _pruefung(a: Any, url: str, befunde: list[dict[str, Any]]) -> tuple[str, str]:
    pid = project(a)
    sid = upload_zip(a, pid).json()["id"]
    _fertig(url, sid, [{**b, "beleg": "token = 'abcd…'", "erklaerung": "Weil."} for b in befunde])
    return pid, sid


def _setzen(c: Any, sid: str, fp: str, status: str, begruendung: str | None = None) -> Any:
    return c.post(
        f"/api/v1/scans/{sid}/befund-status",
        json={"fingerprint": fp * 64, "status": status, "begruendung": begruendung},
    )


def _admin(api: Api, url: str, email: str = "mod@example.org") -> Any:
    m = api.user(email)
    _sql(url, "UPDATE users SET is_admin = true WHERE email = :e", e=email)
    return m


def test_owner_accepts_and_reopens_a_finding(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    pid, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a"), _befund("K", "krit", "b")])

    r = _setzen(a, sid, "a", "akzeptiert", "  Nur im Testaufbau, nie ausgeliefert.  ")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "akzeptiert"
    assert r.json()["begruendung"] == "Nur im Testaufbau, nie ausgeliefert."

    scan = a.get(f"/api/v1/scans/{sid}").json()
    assert scan["befund_status"] == {"a" * 64: r.json()}
    (p,) = a.get("/api/v1/projects").json()
    assert (p["offen_k"], p["offen_h"]) == (1, 0)

    r = _setzen(a, sid, "a", "offen", "wird verworfen")
    assert r.json()["status"] == "offen" and r.json()["begruendung"] is None
    (p,) = a.get("/api/v1/projects").json()
    assert (p["offen_k"], p["offen_h"]) == (1, 1)
    assert pid == p["id"]


def test_status_does_not_change_lights_or_grade(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    _, sid = _pruefung(a, _migrated, [_befund("K", "krit", "a")])
    vorher = a.get(f"/api/v1/scans/{sid}").json()
    _setzen(a, sid, "a", "bestritten", "Fehlalarm: das ist ein Platzhalter.")
    nachher = a.get(f"/api/v1/scans/{sid}").json()
    for feld in ("ampeln", "note", "freigabe", "bericht"):
        assert nachher[feld] == vorher[feld]


def test_reason_required_and_only_known_findings(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    _, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a")])
    assert _setzen(a, sid, "a", "akzeptiert").status_code == 422
    assert _setzen(a, sid, "a", "bestritten", "   ").status_code == 422
    assert _setzen(a, sid, "a", "behoben", "selbst gesetzt").status_code == 422
    assert _setzen(a, sid, "z", "akzeptiert", "gibt es nicht").status_code == 404


def test_fixed_findings_cannot_be_changed(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    pid, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a")])
    _sql(
        _migrated,
        "INSERT INTO finding_status (owner_id, project_id, fingerprint, status) "
        "SELECT owner_id, id, :f, 'behoben' FROM projects WHERE id = :p",
        f="a" * 64,
        p=pid,
    )
    r = _setzen(a, sid, "a", "akzeptiert", "zu spät")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "schon_behoben"


def test_single_checks_have_no_status(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    r = einzel(a)
    assert r.status_code == 202, r.text
    sid = r.json()["id"]
    _fertig(_migrated, sid, [_befund("H", "hoch", "a")])
    assert a.get(f"/api/v1/scans/{sid}").json()["befund_status"] is None
    assert _setzen(a, sid, "a", "akzeptiert", "geht nicht").status_code == 409


def test_user_b_neither_sees_nor_sets_the_status_of_a(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    b = api.user("bert@example.org")
    _, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a")])
    _setzen(a, sid, "a", "akzeptiert", "Begründung von A")
    r = _setzen(b, sid, "a", "offen")
    assert r.status_code == 404 and "Begründung von A" not in r.text
    assert b.get(f"/api/v1/scans/{sid}").status_code == 404
    assert a.get(f"/api/v1/scans/{sid}").json()["befund_status"]["a" * 64]["status"] == (
        "akzeptiert"
    )


def test_moderation_exists_only_for_admins_in_the_browser(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    _, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a")])
    _setzen(a, sid, "a", "bestritten", "Platzhalter, kein echter Schlüssel.")
    assert a.get("/api/v1/auth/ich").json()["moderation"] is False
    assert a.get("/api/v1/moderation/einsprueche").status_code == 404

    m = _admin(api, _migrated)
    assert m.get("/api/v1/auth/ich").json()["moderation"] is True
    token = m.post("/api/v1/tokens", json={"name": "ci"}).json()["token"]
    cli = api.client("https://api.luibui.com")
    r = cli.get("/api/v1/moderation/einsprueche", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_moderator_decides_a_dispute_and_the_owner_sees_it(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    _, sid = _pruefung(a, _migrated, [_befund("H", "hoch", "a"), _befund("M", "mittel", "b")])
    _setzen(a, sid, "a", "bestritten", "Platzhalter, kein echter Schlüssel.")
    _setzen(a, sid, "b", "akzeptiert", "bewusst so")
    m = _admin(api, _migrated)

    (e,) = m.get("/api/v1/moderation/einsprueche").json()
    assert (e["projekt"], e["titel"], e["schwere"]) == ("wetter", "hoch", "H")
    assert e["begruendung"] == "Platzhalter, kein echter Schlüssel."
    assert "beleg" not in e
    assert _sql(_migrated, "SELECT 1 FROM audit_log WHERE action = 'moderation.angesehen'") == []

    detail = m.get(f"/api/v1/moderation/einsprueche/{e['id']}").json()
    assert detail["beleg"] == "token = 'abcd…'"
    ((meta,),) = _sql(_migrated, "SELECT meta FROM audit_log WHERE action = 'moderation.angesehen'")
    assert "Platzhalter" not in str(meta)

    r = m.post(
        f"/api/v1/moderation/einsprueche/{e['id']}/entscheidung",
        json={"ergebnis": "fehlalarm", "notiz": "Regel LB-A01 angepasst."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["eingereicht_am"] == e["eingereicht_am"]
    assert m.get("/api/v1/moderation/einsprueche").json() == []
    assert [x["id"] for x in m.get("/api/v1/moderation/einsprueche?entschieden=true").json()] == [
        e["id"]
    ]

    status = a.get(f"/api/v1/scans/{sid}").json()["befund_status"]["a" * 64]
    assert (status["status"], status["moderation"]) == ("bestritten", "fehlalarm")
    assert status["moderation_notiz"] == "Regel LB-A01 angepasst."

    # A new status by the owner starts over.
    _setzen(a, sid, "a", "bestritten", "noch einmal")
    status = a.get(f"/api/v1/scans/{sid}").json()["befund_status"]["a" * 64]
    assert status["moderation"] is None
    (e2,) = m.get("/api/v1/moderation/einsprueche").json()
    assert e2["id"] == e["id"]

    # Only disputes are visible to the moderation, never accepted findings.
    akzeptiert = _sql(_migrated, "SELECT id FROM finding_status WHERE status = 'akzeptiert'")[0][0]
    assert m.get(f"/api/v1/moderation/einsprueche/{akzeptiert}").status_code == 404
    r = m.post(
        f"/api/v1/moderation/einsprueche/{akzeptiert}/entscheidung", json={"ergebnis": "fehlalarm"}
    )
    assert r.status_code == 404
