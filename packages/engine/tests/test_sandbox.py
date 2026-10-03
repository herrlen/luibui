"""Sprint 6 parts without the sandbox server: decoys (S6-4), protocol check (ADR-001 SB5) and
findings F01–F05 from a protocol (S6-6). The protocols here are hand-written data; nothing runs."""

import json
from pathlib import Path
from typing import Any

import pytest

from luibui_scan.models import Nachweisgrad, Schwere
from luibui_scan.sandbox.befunde import befunde
from luibui_scan.sandbox.koeder import erzeugen
from luibui_scan.sandbox.protokoll import ProtokollError, laden
from luibui_scan.scoring import is_blocklisted

REPO = Path(__file__).resolve().parents[3]
MANIFEST = {"endpunkte": [{"host": "api.wetter.example"}]}


def lauf(uhr: str = "echt", **teile: Any) -> dict[str, Any]:
    return {
        "uhr": uhr,
        "dauer_ms": 1200,
        "abgebrochen": False,
        "prozesse": teile.get("prozesse", []),
        "dateien": teile.get("dateien", []),
        "verbindungen": teile.get("verbindungen", []),
    }


def protokoll(*laeufe: dict[str, Any]) -> dict[str, Any]:
    return laden(json.dumps({"schema": "luibui-sandbox/1", "laeufe": list(laeufe)}).encode())


def ids(p: dict[str, Any], manifest: dict[str, Any] | None = MANIFEST, k: Any = None) -> set[str]:
    return {f.rule_id for f in befunde(p, k or erzeugen(), manifest)}


def test_schema_ships_with_the_engine() -> None:
    packaged = REPO / "packages/engine/luibui_scan/data/sandbox-protokoll.schema.json"
    assert packaged.read_bytes() == (REPO / "spec/sandbox-protokoll.schema.json").read_bytes()


def test_decoys_are_fresh_and_realistic() -> None:
    a, b = erzeugen(), erzeugen()
    assert set(a.werte).isdisjoint(b.werte)
    assert "~/.aws/credentials" in a.dateien and "./.env" in a.dateien
    aws = next(w for w, art in a.werte.items() if art == "AWS-Schlüssel")
    assert aws.startswith("AKIA") and len(aws) == 20 and aws in a.dateien["~/.aws/credentials"]


@pytest.mark.parametrize(
    "roh",
    [
        b"nicht json",
        b'{"schema": "luibui-sandbox/2", "laeufe": []}',
        json.dumps({"schema": "luibui-sandbox/1", "laeufe": [lauf() | {"befehl": "x"}]}).encode(),
        json.dumps({"schema": "luibui-sandbox/1", "laeufe": [lauf(uhr="gruen")]}).encode(),
        b"[" * 100_000,
        b" " * (5 * 1024 * 1024 + 1),
    ],
)
def test_bad_protocols_are_refused(roh: bytes) -> None:
    with pytest.raises(ProtokollError):
        laden(roh)


def test_quiet_package_gives_nothing() -> None:
    p = protokoll(
        lauf(
            prozesse=[
                {
                    "phase": "installation",
                    "befehl": "/bin/sh",
                    "argumente": ["-c", "node build.js"],
                    "skript": True,
                }
            ],
            dateien=[
                {"pfad": "/paket/dist/index.js", "zugriff": "schreiben"},
                {"pfad": "/tmp/x", "zugriff": "schreiben"},
            ],
            verbindungen=[
                {"art": "dns", "ziel": "api.wetter.example"},
                {"art": "tcp", "ziel": "eu.api.wetter.example", "port": 443},
            ],
        ),
        lauf("vorgedreht", verbindungen=[{"art": "dns", "ziel": "api.wetter.example"}]),
    )
    assert ids(p) == set()


def test_f01_undeclared_hosts() -> None:
    p = protokoll(lauf(verbindungen=[{"art": "tcp", "ziel": "sammler.example", "port": 443}]))
    (f,) = befunde(p, erzeugen(), MANIFEST)
    assert f.rule_id == "LB-F01-netzwerk" and f.schwere is Schwere.H
    assert f.nachweisgrad is Nachweisgrad.IN_SANDBOX_BEOBACHTET and "sammler.example:443" in (
        f.beleg or ""
    )
    assert ids(p, manifest={"endpunkte": [{"host": "sammler.example"}]}) == set()


def test_f02_reading_and_sending_decoys() -> None:
    k = erzeugen()
    gh = next(w for w, art in k.werte.items() if art == "GitHub-Token")
    gelesen = protokoll(lauf(dateien=[{"pfad": "~/.ssh/id_ed25519", "zugriff": "lesen"}]))
    (f,) = befunde(gelesen, k, MANIFEST)
    assert f.rule_id == "LB-F02-koeder" and f.schwere is Schwere.K and is_blocklisted(f)
    gesendet = protokoll(
        lauf(
            verbindungen=[
                {
                    "art": "tcp",
                    "ziel": "api.wetter.example",
                    "port": 443,
                    "daten_anfang": f"POST /x token={gh}",
                }
            ]
        )
    )
    (f,) = befunde(gesendet, k, MANIFEST)
    assert "weitergegeben" in f.titel and "GitHub-Token an api.wetter.example" in (f.beleg or "")
    assert gh not in (f.beleg or "")  # never the value itself
    in_dns = protokoll(lauf(verbindungen=[{"art": "dns", "ziel": f"{gh}.sammler.example"}]))
    assert "LB-F02-koeder" in ids(in_dns, k=k)
    # Reading its own files is not a decoy hit.
    assert (
        ids(protokoll(lauf(dateien=[{"pfad": "/paket/config.json", "zugriff": "lesen"}]))) == set()
    )


def test_f03_shell_and_foreign_writes() -> None:
    shell = protokoll(
        lauf(
            prozesse=[
                {"phase": "mcp", "befehl": "/bin/bash", "argumente": ["-c", "id"], "skript": False}
            ]
        )
    )
    assert ids(shell) == {"LB-F03-system"}
    schreibt = protokoll(lauf(dateien=[{"pfad": "/usr/local/bin/node", "zugriff": "schreiben"}]))
    assert ids(schreibt) == {"LB-F03-system"}
    assert ids(
        protokoll(lauf(dateien=[{"pfad": "/paket/../etc/passwd", "zugriff": "schreiben"}]))
    ) == {"LB-F03-system"}


def test_f04_time_bomb() -> None:
    p = protokoll(
        lauf(),
        lauf(
            "vorgedreht",
            verbindungen=[{"art": "dns", "ziel": "api.wetter.example"}],
            dateien=[{"pfad": "/paket/.done", "zugriff": "schreiben"}],
        ),
    )
    (f,) = befunde(p, erzeugen(), MANIFEST)
    assert f.rule_id == "LB-F04-zeitbombe" and is_blocklisted(f)
    assert (
        ids(protokoll(lauf("vorgedreht", dateien=[{"pfad": "/paket/x", "zugriff": "schreiben"}])))
        == set()
    )


def test_f05_persistence() -> None:
    p = protokoll(lauf(dateien=[{"pfad": "~/.bashrc", "zugriff": "schreiben"}]))
    (f,) = befunde(p, erzeugen(), MANIFEST)
    assert f.rule_id == "LB-F05-persistenz" and f.schwere is Schwere.K


def test_evidence_from_the_package_is_masked_and_visible() -> None:
    p = protokoll(lauf(verbindungen=[{"art": "dns", "ziel": "a‮b.sammler.example"}]))
    (f,) = befunde(p, erzeugen(), MANIFEST)
    assert "‮" not in (f.beleg or "") and "<U+202E>" in (f.beleg or "")
