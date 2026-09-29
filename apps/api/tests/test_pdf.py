"""S3-11: the report as PDF, standard and detail. Package text never becomes markup."""

from typing import Any

from luibui_api.pdf import _block, _mit_code, _sichtbar, _t, bericht_als_pdf, dateiname

from .conftest import Api
from .test_scans import project, upload_zip
from .test_uebersicht import _befund, _fertig

BOESE = '<script>alert(1)</script></para><font name="x">&amp; ​‮\x07'


def _bericht(**extra: Any) -> dict[str, Any]:
    befund = _befund("K", "exfil", "a") | {
        "erklaerung": "Liest `~/.ssh` und " + BOESE,
        "beleg": "  eingerückt\n" + BOESE,
        "fix": BOESE,
        "fix_prompt": BOESE,
        "achse": "sicherheit",
    }
    return {
        "scan_art": "intensiv",
        "pruefumfang": "paket",
        "geprueft_am": "2026-09-29T19:50:00+00:00",
        "paket": {"name": "wetter <b>skill</b>", "dateien": 1},
        "ampeln": {"sicherheit": "rot", "dsgvo": "gruen", "gesamt": "rot"},
        "note": 38,
        "freigabe": "blockiert",
        "befunde": [befund],
        "nicht_geprueft": [{"pruefung": BOESE, "grund": BOESE}],
        "hinweise": [BOESE],
        "abdeckung": [{"dateiart": BOESE, "dateien": 1, "geprueft": [BOESE], "offen": []}],
        **extra,
    }


def test_package_text_is_escaped_and_hidden_characters_are_shown() -> None:
    assert _t("<script>&") == "&lt;script&gt;&amp;"
    assert _sichtbar("a​b‮c\x07", "Plex") == "a[U+200B]b[U+202E]c[U+0007]"
    assert _sichtbar("zeile\nnoch", "Plex") == "zeile\nnoch"
    assert "&lt;b&gt;" in _mit_code("`<b>` und <i>")
    assert "<i>" not in _mit_code("`<b>` und <i>")
    assert _block("  x\ny").startswith("&nbsp;&nbsp;x<br/>")


def test_hostile_reports_render_in_both_forms() -> None:
    for umfang in ("standard", "detail"):
        pdf = bericht_als_pdf(_bericht(), umfang)  # type: ignore[arg-type]
        assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    schnell = bericht_als_pdf(_bericht(scan_art="schnell", befunde=[]), "detail")
    assert schnell.startswith(b"%PDF-")


def test_file_name_is_safe_for_the_header() -> None:
    r = _bericht()
    assert dateiname(r, "standard") == "luibui-wetter-b-skill-b-2026-09-29.pdf"
    assert (
        dateiname(r | {"geprueft_am": '"; x'}, "detail")
        == "luibui-wetter-b-skill-b-bericht-detail.pdf"
    )


def test_owner_downloads_standard_and_detail(api: Api, _migrated: str) -> None:
    a = api.user("anna@example.org")
    scan = upload_zip(a, project(a)).json()["id"]
    assert a.get(f"/api/v1/scans/{scan}/bericht.pdf").status_code == 409  # not finished
    _fertig(_migrated, scan, [_befund("K", "exfil", "a"), _befund("H", "hoch", "b")])
    standard = a.get(f"/api/v1/scans/{scan}/bericht.pdf")
    detail = a.get(f"/api/v1/scans/{scan}/bericht.pdf?umfang=detail")
    for r in (standard, detail):
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.headers["cache-control"] == "private, no-store"
        assert r.content.startswith(b"%PDF-")
    assert standard.headers["content-disposition"].startswith('attachment; filename="luibui-p-')
    assert detail.headers["content-disposition"].endswith('-detail.pdf"')
    assert a.get(f"/api/v1/scans/{scan}/bericht.pdf?umfang=alles").status_code == 422


def test_nobody_else_gets_the_pdf(api: Api, _migrated: str) -> None:
    a, b = api.user("anna@example.org"), api.user("bert@example.org")
    scan = upload_zip(a, project(a)).json()["id"]
    _fertig(_migrated, scan, [_befund("K", "geheim", "a")])
    assert b.get(f"/api/v1/scans/{scan}/bericht.pdf").status_code == 404
    assert api.client().get(f"/api/v1/scans/{scan}/bericht.pdf").status_code == 401


def test_example_pdf_on_the_website_matches_the_example_report() -> None:
    """apps/web/public/beispielbericht.pdf is built from content/beispielbericht.json. After
    changing either, rebuild it: python -m luibui_api.pdf <json> <pdf>."""
    import json
    from pathlib import Path

    web = Path(__file__).resolve().parents[2] / "web"
    report = json.loads((web / "content" / "beispielbericht.json").read_text(encoding="utf-8"))
    assert (
        bericht_als_pdf(report, "detail", fest=True)
        == (web / "public" / "beispielbericht.pdf").read_bytes()
    )
