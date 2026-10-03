"""S4-6 / H01: only additions between two manifests count."""

from typing import Any

from luibui_api.diff import aenderungen


def m(**anders: Any) -> dict[str, Any]:
    basis: dict[str, Any] = {
        "rechte": {
            "netzwerk": True,
            "dateien": {"lesen": ["./daten/**"], "schreiben": []},
            "shell": False,
            "zugangsdaten": False,
            "umgebungsvariablen": [],
        },
        "endpunkte": [
            {"host": "api.wetter.example", "land": "DE", "datenkategorien": ["nutzereingaben"]}
        ],
        "datenkategorien": ["nutzereingaben"],
    }
    return basis | anders


def texte(alt: dict[str, Any] | None, neu: dict[str, Any]) -> list[str]:
    return [a["text"] for a in aenderungen(alt, neu)]


def test_first_version_and_unchanged_have_no_changes() -> None:
    assert texte(None, m()) == []
    assert texte(m(), m()) == []


def test_new_rights_endpoints_countries_and_data() -> None:
    neu = m(
        rechte={
            "netzwerk": True,
            "dateien": {"lesen": ["./daten/**", "~/.ssh/*"], "schreiben": ["./out/*"]},
            "shell": True,
            "zugangsdaten": True,
            "umgebungsvariablen": ["OPENAI_API_KEY"],
        },
        endpunkte=[
            {"host": "api.wetter.example", "land": "US", "datenkategorien": ["nutzereingaben"]},
            {"host": "sammler.example", "land": "CN", "datenkategorien": []},
        ],
        datenkategorien=["nutzereingaben", "standortdaten"],
    )
    assert texte(m(), neu) == [
        "Shell-Befehle neu",
        "Zugangsdaten neu",
        "Liest neu: ~/.ssh/*",
        "Schreibt neu: ./out/*",
        "Liest neu die Umgebungsvariable OPENAI_API_KEY",
        "api.wetter.example jetzt in US statt DE",
        "Neuer Endpunkt sammler.example (CN)",
        "Verarbeitet neu: standortdaten",
    ]


def test_more_data_to_a_known_endpoint_and_removals_do_not_count() -> None:
    mehr = m(endpunkte=[{"host": "api.wetter.example", "land": "DE",
                         "datenkategorien": ["nutzereingaben", "standortdaten"]}])  # fmt: skip
    assert texte(m(), mehr) == ["Schickt neu standortdaten an api.wetter.example"]
    weniger = m(rechte={"netzwerk": False, "dateien": {"lesen": [], "schreiben": []}}, endpunkte=[])
    assert texte(m(), weniger) == []


def test_broken_manifests_do_not_crash() -> None:
    assert texte({"rechte": "x", "endpunkte": "y"}, {"rechte": [], "endpunkte": [1, None]}) == []
