"""S3-5: history of a project and the comparison of two checks."""

from typing import Any

from sqlalchemy import create_engine, text

from .conftest import Api
from .test_scans import project, upload_zip
from .test_uebersicht import _befund, _fertig


def _pruefung(c: Any, url: str, pid: str, befunde: list[dict[str, Any]], note: int) -> str:
    sid = upload_zip(c, pid).json()["id"]
    _fertig(url, sid, befunde)
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE scans SET note = :n, ampel_gesamt = 'rot' WHERE id = :i"),
            {"n": note, "i": sid},
        )
    engine.dispose()
    return sid


def test_history_counts_findings_per_severity_oldest_first(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    erste = _pruefung(
        c,
        _migrated,
        pid,
        [_befund("K", "a", "a"), _befund("H", "b", "b"), _befund("H", "c", "c")],
        20,
    )
    upload_zip(c, pid)  # still waiting: not part of the history
    zweite = _pruefung(c, _migrated, pid, [_befund("M", "d", "d")], 85)
    punkte = c.get(f"/api/v1/projects/{pid}/verlauf").json()
    assert [p["scan_id"] for p in punkte] == [erste, zweite]
    assert punkte[0]["befunde"] == {"K": 1, "H": 2, "M": 0, "N": 0, "I": 0}
    assert punkte[1]["befunde"] == {"K": 0, "H": 0, "M": 1, "N": 0, "I": 0}
    assert [p["note"] for p in punkte] == [20, 85]


def test_history_of_an_empty_project(api: Api) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    assert c.get(f"/api/v1/projects/{pid}/verlauf").json() == []
    r = c.get(f"/api/v1/projects/{pid}/vergleich")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "zu_wenig_pruefungen"


def test_comparison_new_fixed_unchanged(api: Api, _migrated: str) -> None:
    c = api.user("anna@example.org")
    pid = project(c)
    erste = _pruefung(
        c, _migrated, pid, [_befund("K", "weg", "a"), _befund("H", "bleibt", "b")], 30
    )
    zweite = _pruefung(
        c, _migrated, pid, [_befund("H", "bleibt", "b", zeile=9), _befund("M", "neu", "c")], 70
    )
    standard = c.get(f"/api/v1/projects/{pid}/vergleich").json()
    gewaehlt = c.get(f"/api/v1/projects/{pid}/vergleich?von={zweite}&bis={erste}").json()
    for v in (standard, gewaehlt):  # newest against the one before, in either order
        assert (v["von"]["scan_id"], v["bis"]["scan_id"]) == (erste, zweite)
        assert [e["titel"] for e in v["neu"]] == ["neu"]
        assert [e["titel"] for e in v["behoben"]] == ["weg"]
        assert [(e["titel"], e["zeile"]) for e in v["unveraendert"]] == [("bleibt", 9)]
        assert v["gleicher_umfang"] is True
        assert (v["von"]["note"], v["bis"]["note"]) == (30, 70)


def test_comparison_only_within_the_own_project(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    pid = project(a)
    erste = _pruefung(a, _migrated, pid, [_befund("K", "x", "a")], 10)
    zweite = _pruefung(a, _migrated, pid, [], 100)
    anderes = project(a, "anderes")
    fremd = _pruefung(a, _migrated, anderes, [], 100)
    offen = upload_zip(a, pid).json()["id"]
    url = f"/api/v1/projects/{pid}/vergleich"
    assert a.get(f"{url}?von={erste}&bis={fremd}").status_code == 404  # other project
    assert a.get(f"{url}?von={erste}&bis={offen}").status_code == 404  # not finished
    assert a.get(f"{url}?von={erste}").status_code == 422
    b = api.user("bert@example.org")
    assert b.get(f"{url}?von={erste}&bis={zweite}").status_code == 404
    assert b.get(f"/api/v1/projects/{pid}/verlauf").status_code == 404
