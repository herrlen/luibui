"""Finding model. Mirrors spec/finding.schema.json; tests keep both in sync."""

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Ebene(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"


class Schwere(StrEnum):
    K = "K"
    H = "H"
    M = "M"
    N = "N"
    I = "I"  # noqa: E741 - severity code from the concept


class Achse(StrEnum):
    SICHERHEIT = "sicherheit"
    DSGVO = "dsgvo"


class Nachweisgrad(StrEnum):
    STATISCH_ERKANNT = "statisch_erkannt"
    PER_LLM_BEWERTET = "per_llm_bewertet"
    IN_SANDBOX_BEOBACHTET = "in_sandbox_beobachtet"
    IM_TEST_BEOBACHTET = "im_test_beobachtet"
    SELBSTAUSKUNFT = "selbstauskunft"


class ScanArt(StrEnum):
    SCHNELL = "schnell"
    INTENSIV = "intensiv"
    LOKAL = "lokal"


class Pakettyp(StrEnum):
    """Detected by the inventory (S1-4), independent of what luibui.json declares."""

    SKILL = "skill"
    MCP_SERVER = "mcp-server"
    PLUGIN = "plugin"
    TOOL = "tool"
    GEMISCHT = "gemischt"
    UNBEKANNT = "unbekannt"


class Pruefumfang(StrEnum):
    PAKET = "paket"
    AUSWAHL = "auswahl"
    EINZELDATEI = "einzeldatei"


RULE_ID_PATTERN = (
    r"^(LB-[A-I][0-9]{1,2}-[a-z0-9]+(-[a-z0-9]+)*|ATR-[A-Za-z0-9-]+|[a-z][a-z0-9-]*:[^\s]+)$"
)
MAX_BELEG_LINES = 5
_SHA256 = r"^[0-9a-f]{64}$"

Sha256 = Annotated[str, Field(pattern=_SHA256)]


class Finding(BaseModel):
    """One finding. Texts are plain German; ``beleg`` is always rendered as escaped text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str = Field(max_length=200, pattern=RULE_ID_PATTERN)
    ebene: Ebene
    schwere: Schwere
    achse: Achse
    titel: str = Field(min_length=1, max_length=200)
    erklaerung: str = Field(min_length=1, max_length=4000)
    datei: str | None = Field(max_length=1024)
    zeile: int | None = Field(ge=1)
    beleg: str | None = Field(max_length=2000)
    nachweisgrad: Nachweisgrad
    normbezug: tuple[Annotated[str, Field(min_length=1, max_length=100)], ...]
    fix: str = Field(min_length=1, max_length=4000)
    fix_prompt: str = Field(max_length=8000)
    analyzer: str | None = Field(default=None, max_length=100)
    fingerprint: Sha256 | None = None
    hochgestuft_von: Schwere | None = None
    verweise: tuple[Sha256, ...] | None = None

    @field_validator("datei")
    @classmethod
    def _relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value or value.startswith("/") or "\\" in value or "\x00" in value:
            raise ValueError("datei muss ein relativer Pfad mit / sein")
        if ".." in value.split("/"):
            raise ValueError("datei darf kein '..'-Segment enthalten")
        return value

    @field_validator("beleg")
    @classmethod
    def _max_lines(cls, value: str | None) -> str | None:
        if value is not None and value.count("\n") >= MAX_BELEG_LINES:
            raise ValueError(f"beleg darf höchstens {MAX_BELEG_LINES} Zeilen haben")
        return value

    @field_validator("normbezug", "verweise")
    @classmethod
    def _unique(cls, value: tuple[str, ...] | None) -> tuple[str, ...] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Einträge müssen eindeutig sein")
        return value

    def to_json_dict(self) -> dict[str, object]:
        """Serialize for the report; optional fields that are unset are omitted."""
        optional = {"analyzer", "fingerprint", "hochgestuft_von", "verweise"}
        data = self.model_dump(mode="json")
        return {k: v for k, v in data.items() if not (k in optional and v is None)}


def is_valid_rule_id(rule_id: str) -> bool:
    return re.fullmatch(RULE_ID_PATTERN, rule_id) is not None
