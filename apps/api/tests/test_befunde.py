"""S3-7: finding status (accepted, disputed, fixed) and the moderation of disputes."""

from typing import Any

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_scans import project, upload_zip
from .test_uebersicht import _befund, _fertig

A = "a" * 64
B = "b" * 64


def _projekt_mit_pruefung(api: Api, url: str, befunde: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    c = api.user("anna@example.org")
    pid = project(c)
    scan = upload_zip(c, pid).json()["id"]
    _fertig(url, scan, befunde)
    return c, pid, scan


def _setzen(c, pid: str, fp: str, status: str, begruendung: str | None = None):  # type: ignore[no-untyped-def]
    return c.post(
        f"/api/v1/projects/{pid}/befunde/{fp}/status",
        json={"status": status, "begruendung": begruendung},
    )


def _admin(url: str, email: str) -> None:
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET is_admin = true WHERE email = :e"), {"e": email})
    engine.dispose()


def test_accepting_needs_a_reason_and_hides_it_from_the_overview(api: Api, _migrated: str) -> None:
    c, pid, scan = _projekt_mit_pruefung(
        api, _migrated, [_befund("K", "exfil", "a"), _befund("H", "hoch", "b")]
    )
    assert _setzen(c, pid, A, "akzeptiert").status_code == 422
    assert _setzen(c, pid, A, "akzeptiert", "  kurz ").status_code == 422
    r = _setzen(c, pid, A, "akzeptiert", "Nur Testdaten, nie ausgeliefert")
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["moderation"]) == ("akzeptiert", None)
    s = c.get(f"/api/v1/scans/{scan}").json()
    assert s["befund_status"][A]["begruendung"] == "Nur Testdaten, nie ausgeliefert"
    offen = [b["rule_id"] for b in c.get("/api/v1/projects/offene-befunde").json()]
    assert offen == ["LB-A01-hoch"]
    # back to open: the reason goes away
    r = _setzen(c, pid, A, "offen", "egal")
    assert (r.json()["status"], r.json()["begruendung"]) == ("offen", None)
    offen = [b["rule_id"] for b in c.get("/api/v1/projects/offene-befunde").json()]
    assert offen == ["LB-A01-exfil", "LB-A01-hoch"]


def test_only_findings_of_the_latest_check(api: Api, _migrated: str) -> None:
    c, pid, _ = _projekt_mit_pruefung(api, _migrated, [_befund("K", "exfil", "a")])
    assert _setzen(c, pid, "c" * 64, "akzeptiert", "gibt es nicht").status_code == 404
    assert _setzen(c, pid, "nicht-hex", "akzeptiert", "kaputt ...").status_code == 404
    assert _setzen(c, pid, A, "behoben", "von Hand geht nicht").status_code == 422


def test_fixed_findings_and_status_carry_over(api: Api, _migrated: str) -> None:
    c, pid, erste = _projekt_mit_pruefung(
        api, _migrated, [_befund("K", "exfil", "a"), _befund("M", "mittel", "b")]
    )
    assert _setzen(c, pid, B, "akzeptiert", "So gewollt, siehe README").status_code == 200
    zweite = upload_zip(c, pid).json()["id"]
    _fertig(_migrated, zweite, [_befund("M", "mittel", "b")])
    s = c.get(f"/api/v1/scans/{zweite}").json()
    assert [(b["fingerprint"], b["titel"], b["schwere"]) for b in s["behoben"]] == [
        (A, "exfil", "K")
    ]
    assert s["befund_status"][B]["status"] == "akzeptiert"  # same fingerprint, same status
    assert c.get(f"/api/v1/scans/{erste}").json()["behoben"] == []
    # the fixed finding is no longer in the latest check, so it cannot be changed any more
    assert _setzen(c, pid, A, "akzeptiert", "zu spät dafür").status_code == 404


def test_dispute_goes_to_moderation(api: Api, _migrated: str) -> None:
    c, pid, scan = _projekt_mit_pruefung(api, _migrated, [_befund("H", "hoch", "a")])
    r = _setzen(c, pid, A, "bestritten", "Das ist <b>ein</b> Beispiel in der Doku")
    assert r.status_code == 200
    # an ordinary user, also the author, does not see the moderation view
    assert c.get("/api/v1/admin/einsprueche").status_code == 404
    mod = api.user("moderation@example.org")
    assert mod.get("/api/v1/admin/einsprueche").status_code == 404
    _admin(_migrated, "moderation@example.org")
    (e,) = mod.get("/api/v1/admin/einsprueche").json()
    assert (e["rule_id"], e["titel"], e["datei"], e["zeile"]) == (
        "LB-A01-hoch",
        "hoch",
        "SKILL.md",
        1,
    )
    assert e["begruendung"] == "Das ist <b>ein</b> Beispiel in der Doku"  # stored as text
    assert e["moderation"] is None
    assert "fingerprint" not in e and "project_id" not in e  # nothing that leads to the account
    url = f"/api/v1/admin/einsprueche/{e['id']}/entscheidung"
    assert c.post(url, json={"entscheidung": "fehlalarm"}).status_code == 404
    assert mod.post(url, json={"entscheidung": "vielleicht"}).status_code == 422
    r = mod.post(url, json={"entscheidung": "fehlalarm"})
    assert r.status_code == 200 and r.json()["moderation"] == "fehlalarm"
    # the author sees the outcome on the report; a new dispute waits again
    assert c.get(f"/api/v1/scans/{scan}").json()["befund_status"][A]["moderation"] == "fehlalarm"
    assert (
        _setzen(c, pid, A, "bestritten", "Neue Begründung, bitte erneut").json()["moderation"]
        is None
    )
    engine = create_engine(_migrated)
    with engine.connect() as conn:
        aktionen = [
            r[0] for r in conn.execute(text("SELECT action FROM audit_log ORDER BY created_at"))
        ]
    engine.dispose()
    assert "admin.einsprueche_gelesen" in aktionen and "admin.einspruch_entschieden" in aktionen


def test_accepted_findings_are_not_in_moderation(api: Api, _migrated: str) -> None:
    c, pid, _ = _projekt_mit_pruefung(api, _migrated, [_befund("H", "hoch", "a")])
    _setzen(c, pid, A, "akzeptiert", "bewusst so gelassen")
    mod = api.user("moderation@example.org")
    _admin(_migrated, "moderation@example.org")
    assert mod.get("/api/v1/admin/einsprueche").json() == []
