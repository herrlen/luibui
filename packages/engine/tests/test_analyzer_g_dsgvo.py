"""S2-4: DSGVO and rights (G01–G06). Endpoints from the code, countries from the maintained list,
compared with luibui.json. Nothing is looked up online."""

import json
from pathlib import Path
from typing import Any

import pytest

from luibui_scan.analyzers._common import rules_dir
from luibui_scan.analyzers.g_dsgvo import DsgvoAnalyzer, laender
from luibui_scan.context import ScanContext
from luibui_scan.inventory import build_inventory
from luibui_scan.models import Achse, Finding, Pruefumfang, ScanArt, Schwere

REPO = Path(__file__).resolve().parents[3]
MARK = "# LUIBUI-TESTFIXTURE: entschärft, nicht ausführen\n"


def manifest(**over: Any) -> str:
    base: dict[str, Any] = {
        "schema_version": "1",
        "name": "beispiel/tool",
        "version": "1.0.0",
        "typ": "tool",
        "beschreibung": "Ein Beispiel.",
        "lizenz": "MIT",
        "rechte": {
            "netzwerk": True,
            "dateien": {"lesen": [], "schreiben": []},
            "shell": False,
            "zugangsdaten": True,
            "umgebungsvariablen": ["MISTRAL_API_KEY"],
        },
        "endpunkte": [
            {
                "host": "api.mistral.ai",
                "zweck": "Text erzeugen",
                "land": "FR",
                "datenkategorien": ["nutzereingaben"],
            }
        ],
        "datenkategorien": ["nutzereingaben", "zugangsdaten"],
    }
    base.update(over)
    return json.dumps(base)


CODE = MARK + (
    "import os\nimport requests\n\n"
    "def frage(text):\n"
    "    key = os.environ['MISTRAL_API_KEY']\n"
    "    return requests.post('https://api.mistral.ai/v1/chat', json={'q': text},"
    " headers={'Authorization': key})\n"
)


def analyze(tmp_path: Path, files: dict[str, str]) -> list[Finding]:
    root = tmp_path / "pkg"
    for rel, content in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(content)
    inv = build_inventory(root)
    ctx = ScanContext(
        root=root,
        scan_art=ScanArt.INTENSIV,
        pruefumfang=Pruefumfang.PAKET if "luibui.json" in files else Pruefumfang.AUSWAHL,
        inventory=inv.entries,
        pakettyp=inv.pakettyp,
    )
    return DsgvoAnalyzer().analyze(ctx)


def rules(findings: list[Finding]) -> list[str]:
    return [f.rule_id for f in findings]


def test_country_list_is_consistent() -> None:
    ld = laender(rules_dir())
    assert not ld.ewr & set(ld.angemessen) and "US" not in ld.ewr | set(ld.angemessen)
    for host, entry in ld.hosts.items():
        assert len(entry["land"]) == 2 and entry["land"].isupper(), host
    assert all(host in ld.hosts for host in ld.sdks.values())


def test_packaged_schema_matches_spec() -> None:
    packaged = REPO / "packages" / "engine" / "luibui_scan" / "data" / "luibui.schema.json"
    assert packaged.read_bytes() == (REPO / "spec" / "luibui.schema.json").read_bytes()


def test_declared_package_has_only_the_self_declaration(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"luibui.json": manifest(), "tool.py": CODE})
    assert rules(found) == ["LB-G06-selbstauskunft"]
    assert found[0].schwere is Schwere.I and found[0].achse is Achse.DSGVO


# --- without a manifest: only G02 --------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "rule", "schwere"),
    [
        ("https://api.deepseek.com/chat", "LB-G02-drittland", Schwere.H),
        ("https://api.openai.com/v1/chat", "LB-G02-drittland", Schwere.M),
        ("https://api.unbekannt-luibui.de/x", "LB-G02-land-unbekannt", Schwere.I),
    ],
)
def test_g02_without_manifest(tmp_path: Path, url: str, rule: str, schwere: Schwere) -> None:
    code = MARK + f"import requests\nrequests.get('{url}')\n"
    found = analyze(tmp_path, {"t.py": code})
    assert [(f.rule_id, f.schwere) for f in found] == [(rule, schwere)]


@pytest.mark.parametrize(
    "code",
    [
        "import requests\nrequests.get('https://api.mistral.ai/x')\n",  # EWR
        "import requests\nrequests.get('https://api.open-meteo.com/x')\n",  # Schweiz
        "import requests\nrequests.get('http://localhost:8080/x')\n",
        "import requests\nrequests.get('https://api.example.com/x')\n",
        '"""Doku: https://api.deepseek.com"""\nimport requests\n',  # docstring
        "import requests\nHTML = '''<html>\n<a href=\"https://api.deepseek.com\">x</a>\n</html>'''\n",
        "NS = 'http://www.google.com/schemas/sitemap-image/1.1'\nimport requests\n",
        "LINK = 'https://api.deepseek.com'  # no network library: a link, not a target\n",
    ],
)
def test_no_g02_finding(tmp_path: Path, code: str) -> None:
    assert analyze(tmp_path, {"t.py": MARK + code}) == []


def test_sdk_import_is_an_endpoint(tmp_path: Path) -> None:
    code = MARK + "from openai import OpenAI\nclient = OpenAI()\n"
    f = analyze(tmp_path, {"t.py": code})[0]
    assert f.rule_id == "LB-G02-drittland" and "api.openai.com" in f.titel


def test_typescript_and_shell(tmp_path: Path) -> None:
    files = {
        "index.ts": "// x\nimport Anthropic from '@anthropic-ai/sdk';\n",
        "run.sh": MARK + "curl -s https://api.deepseek.com/v1/x\n# curl https://api.moonshot.cn\n",
    }
    found = {f.titel for f in analyze(tmp_path, files)}
    assert any("api.anthropic.com" in t for t in found)
    assert any("api.deepseek.com" in t for t in found)
    assert not any("moonshot" in t for t in found)  # comment line


# --- with a manifest: G01, G03–G06 ------------------------------------------------------------


def test_g01_invalid_manifest(tmp_path: Path) -> None:
    found = analyze(tmp_path, {"luibui.json": json.dumps({"name": "x"}), "t.py": "x = 1\n"})
    assert "LB-G01-manifest-ungueltig" in rules(found)
    assert (
        analyze(tmp_path / "b", {"luibui.json": "{kaputt", "t.py": "x=1\n"})[0].schwere is Schwere.M
    )


def test_g01_type_differs_from_detection(tmp_path: Path) -> None:
    files = {
        "luibui.json": manifest(typ="skill"),
        "server.py": "from mcp.server.fastmcp import FastMCP\n",
    }
    assert "LB-G01-typ-abweichend" in rules(analyze(tmp_path, files))


def test_g03_undeclared_endpoint(tmp_path: Path) -> None:
    code = CODE + "requests.get('https://api.deepseek.com/x')\n"
    found = analyze(tmp_path, {"luibui.json": manifest(), "tool.py": code})
    g03 = next(f for f in found if f.rule_id == "LB-G03-endpunkt-undeklariert")
    assert g03.schwere is Schwere.H and "api.deepseek.com" in g03.titel
    assert "LB-G02-drittland" in rules(found)


def test_wildcard_declaration(tmp_path: Path) -> None:
    endpunkte = [
        {"host": "*.mistral.ai", "zweck": "x", "land": "FR", "datenkategorien": ["nutzereingaben"]}
    ]
    found = analyze(tmp_path, {"luibui.json": manifest(endpunkte=endpunkte), "tool.py": CODE})
    assert "LB-G03-endpunkt-undeklariert" not in rules(found)


def test_g02_us_with_legal_basis_is_a_hint(tmp_path: Path) -> None:
    ep = {
        "host": "api.openai.com",
        "zweck": "x",
        "land": "US",
        "datenkategorien": ["nutzereingaben"],
    }
    code = MARK + "import requests\nrequests.post('https://api.openai.com/v1/x')\n"
    ohne = analyze(tmp_path, {"luibui.json": manifest(endpunkte=[ep]), "t.py": code})
    assert ("LB-G02-drittland", Schwere.M) in [(f.rule_id, f.schwere) for f in ohne]
    ep["rechtsgrundlage"] = "standardvertragsklauseln"
    mit = analyze(tmp_path / "b", {"luibui.json": manifest(endpunkte=[ep]), "t.py": code})
    assert ("LB-G02-drittland", Schwere.I) in [(f.rule_id, f.schwere) for f in mit]


def test_g04_undeclared_rights(tmp_path: Path) -> None:
    code = CODE + (
        "import subprocess\nsubprocess.run(['echo', 'x'])\n"
        "open('out.txt', 'w').write('x')\nos.getenv('WEITERE_VARIABLE')\n"
    )
    found = analyze(tmp_path, {"luibui.json": manifest(), "tool.py": code})
    titel = {f.titel for f in found if f.rule_id == "LB-G04-recht-undeklariert"}
    assert titel == {
        "Recht nicht deklariert: Shell",
        "Recht nicht deklariert: Dateien schreiben",
        "Umgebungsvariablen nicht deklariert",
    }


def test_g04_credentials_and_g05_category(tmp_path: Path) -> None:
    rechte = {
        "netzwerk": True,
        "dateien": {"lesen": [], "schreiben": []},
        "shell": False,
        "zugangsdaten": False,
        "umgebungsvariablen": ["MISTRAL_API_KEY"],
    }
    files = {
        "luibui.json": manifest(rechte=rechte, datenkategorien=["nutzereingaben"]),
        "tool.py": CODE,
    }
    found = analyze(tmp_path, files)
    assert "Recht nicht deklariert: Zugangsdaten" in {f.titel for f in found}
    assert "LB-G05-datenkategorie-fehlt" in rules(found)


def test_all_findings_are_on_the_dsgvo_axis(tmp_path: Path) -> None:
    code = CODE + "requests.get('https://api.deepseek.com/x')\n"
    found = analyze(tmp_path, {"luibui.json": manifest(typ="skill"), "tool.py": code})
    assert found and all(f.achse is Achse.DSGVO for f in found)


def test_quick_scan_has_no_dsgvo_analysis() -> None:
    assert ScanArt.SCHNELL not in DsgvoAnalyzer.info.scan_arts
