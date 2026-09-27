"""Rejection of an input. Every intake check raises ``IntakeRejectedError`` and stops the intake."""

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from luibui_scan.models import Finding


class Ablehnung(StrEnum):
    """Machine code for why an input was rejected. The report maps it to a finding (S1-10)."""

    PFAD_AUSSERHALB = "pfad_ausserhalb"
    """``..`` segment, absolute path or drive letter."""
    UNGUELTIGER_NAME = "ungueltiger_name"
    """Empty segment, ``.``, backslash, NUL or control character in a name."""
    NAME_ZU_LANG = "name_zu_lang"
    DOPPELTER_NAME = "doppelter_name"
    """Two entries that are equal after NFC and case folding, or a file that is also a folder."""
    ZU_TIEF = "zu_tief"
    VERKNUEPFUNG = "verknuepfung"
    """Symlink, hardlink, device or any other entry that is neither a file nor a folder."""
    VERSCHLUESSELT = "verschluesselt"
    ZU_GROSS = "zu_gross"
    ZU_VIELE_DATEIEN = "zu_viele_dateien"
    KOMPRESSIONSRATE = "kompressionsrate"
    DEFEKTES_ARCHIV = "defektes_archiv"


_TEXT = {
    Ablehnung.PFAD_AUSSERHALB: "Ein Pfad zeigt aus dem Paket heraus.",
    Ablehnung.UNGUELTIGER_NAME: "Ein Datei- oder Ordnername ist ungültig.",
    Ablehnung.NAME_ZU_LANG: "Ein Datei- oder Ordnername ist zu lang.",
    Ablehnung.DOPPELTER_NAME: "Zwei Einträge haben denselben Namen.",
    Ablehnung.ZU_TIEF: "Die Ordner sind zu tief verschachtelt.",
    Ablehnung.VERKNUEPFUNG: "Das Paket enthält eine Verknüpfung oder Sonderdatei.",
    Ablehnung.VERSCHLUESSELT: "Das Archiv enthält verschlüsselte Einträge.",
    Ablehnung.ZU_GROSS: "Die Eingabe ist zu groß.",
    Ablehnung.ZU_VIELE_DATEIEN: "Die Eingabe enthält zu viele Dateien.",
    Ablehnung.KOMPRESSIONSRATE: (
        "Das Archiv ist ungewöhnlich stark komprimiert (mögliche Zip-Bombe)."
    ),
    Ablehnung.DEFEKTES_ARCHIV: "Das Archiv ist beschädigt oder wird nicht unterstützt.",
}


class IntakeRejectedError(Exception):
    """The input is refused as a whole; nothing from it may be analyzed.

    ``pfad`` is the offending name exactly as supplied. It is hostile data: log it with ``%r`` and
    render it only as escaped text.
    """

    def __init__(
        self, grund: Ablehnung, pfad: str | None = None, detail: str | None = None
    ) -> None:
        self.grund = grund
        self.pfad = pfad
        self.detail = detail
        super().__init__(f"{grund.value}: {pfad!r}" if pfad is not None else grund.value)

    @property
    def text(self) -> str:
        """Plain German explanation for the user, without package content."""
        return _TEXT[self.grund] if self.detail is None else f"{_TEXT[self.grund]} {self.detail}"


# --- finding A01 (docs/luibui_Pruefkatalog.md §11) -------------------------------------------

_A01: dict[Ablehnung, tuple[str, str, str]] = {
    Ablehnung.PFAD_AUSSERHALB: (
        "H",
        "Ein Eintrag würde außerhalb des Pakets landen (`..`, absoluter Pfad oder Laufwerk). "
        "So überschreiben Archive beim Entpacken fremde Dateien (Zip-Slip).",
        "Das Paket ohne Pfade mit `..` oder `/` am Anfang neu packen.",
    ),
    Ablehnung.VERKNUEPFUNG: (
        "H",
        "Das Paket enthält eine Verknüpfung (Symlink, Hardlink) oder Sonderdatei. Sie kann auf "
        "Dateien außerhalb des Pakets zeigen, zum Beispiel auf Zugangsdaten.",
        "Verknüpfungen durch echte Dateien ersetzen.",
    ),
    Ablehnung.KOMPRESSIONSRATE: (
        "H",
        "Das Archiv ist über 100-fach komprimiert. So sehen Zip-Bomben aus, die beim Entpacken "
        "Platte oder Speicher füllen.",
        "Große, gleichförmige Dateien aus dem Paket entfernen.",
    ),
    Ablehnung.VERSCHLUESSELT: (
        "M",
        "Das Archiv enthält verschlüsselte Einträge. Ihr Inhalt lässt sich nicht prüfen.",
        "Das Paket ohne Passwort packen.",
    ),
    Ablehnung.DOPPELTER_NAME: (
        "M",
        "Zwei Einträge heißen gleich, wenn man Groß- und Kleinschreibung oder Unicode-"
        "Schreibweisen gleichsetzt. Je nach System gewinnt ein anderer.",
        "Eine der beiden Dateien umbenennen.",
    ),
    Ablehnung.UNGUELTIGER_NAME: (
        "M",
        "Ein Name enthält Steuerzeichen, Backslashes oder leere Pfadteile.",
        "Die Datei umbenennen.",
    ),
    Ablehnung.NAME_ZU_LANG: ("N", "Ein Datei- oder Pfadname ist zu lang.", "Kürzer benennen."),
    Ablehnung.ZU_TIEF: ("N", "Ordner sind tiefer als 20 Ebenen verschachtelt.", "Flacher ordnen."),
    Ablehnung.ZU_GROSS: ("N", "Die Eingabe überschreitet die Größengrenze.", "Kleiner packen."),
    Ablehnung.ZU_VIELE_DATEIEN: (
        "N",
        "Die Eingabe enthält mehr Dateien als erlaubt.",
        "Unnötige Dateien entfernen.",
    ),
    Ablehnung.DEFEKTES_ARCHIV: (
        "N",
        "Das Archiv ist beschädigt oder nutzt ein nicht unterstütztes Format.",
        "Neu als normales ZIP packen.",
    ),
}


def rejection_finding(exc: IntakeRejectedError) -> "Finding":
    """The rejection as finding A01. The name goes into ``beleg`` with invisible characters
    escaped; ``datei`` is set only if the name is a valid relative path."""
    from luibui_scan.models import Achse, Ebene, Finding, Nachweisgrad, Schwere

    schwere, erklaerung, fix = _A01[exc.grund]
    datei = exc.pfad
    if datei is not None and (
        not datei
        or datei.startswith("/")
        or "\\" in datei
        or "\x00" in datei
        or ".." in datei.split("/")
        or len(datei) > 1024
    ):
        datei = None
    beleg = None if exc.pfad is None else ascii(exc.pfad)[1:-1][:500]
    return Finding(
        rule_id=f"LB-A01-{exc.grund.value.replace('_', '-')}",
        ebene=Ebene.A,
        schwere=Schwere(schwere),
        achse=Achse.SICHERHEIT,
        titel=_TEXT[exc.grund],
        erklaerung=erklaerung,
        datei=datei,
        zeile=None,
        beleg=beleg,
        nachweisgrad=Nachweisgrad.STATISCH_ERKANNT,
        normbezug=("OWASP-ASI04",),
        fix=fix,
        fix_prompt="",
    )
