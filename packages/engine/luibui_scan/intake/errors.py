"""Rejection of an input. Every intake check raises ``IntakeRejectedError`` and stops the intake."""

from enum import StrEnum


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
