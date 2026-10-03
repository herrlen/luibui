"""Decoy credentials for one sandbox run (S6-4, Prüfkatalog F02).

Fresh random values per run, in the formats real tools use, so a package that looks for keys
finds them. They are worthless and appear nowhere else: any read of the decoy files and any
appearance of a value in traffic, DNS names or written files is evidence.
"""

import secrets
import string
from dataclasses import dataclass, field

_ALNUM = string.ascii_letters + string.digits
_UPPER = string.ascii_uppercase + string.digits


def _zufall(zeichen: str, n: int) -> str:
    return "".join(secrets.choice(zeichen) for _ in range(n))


@dataclass(frozen=True, slots=True)
class KoederSatz:
    dateien: dict[str, str]
    """Path below the sandbox HOME (``~/…``) or the package folder (``./…``) → content."""
    umgebung: dict[str, str]
    werte: dict[str, str] = field(default_factory=dict)
    """Secret value → kind, to recognise it anywhere in the protocol."""

    def pfade(self) -> frozenset[str]:
        return frozenset(self.dateien)


def erzeugen() -> KoederSatz:
    aws_id = "AKIA" + _zufall(_UPPER, 16)
    aws_secret = _zufall(_ALNUM + "/+", 40)
    gh = "ghp_" + _zufall(_ALNUM, 36)
    openai = "sk-proj-" + _zufall(_ALNUM, 48)
    npm = "npm_" + _zufall(_ALNUM, 36)
    ssh = _zufall(_ALNUM + "/+", 280)
    dateien = {
        "~/.aws/credentials": (
            f"[default]\naws_access_key_id = {aws_id}\naws_secret_access_key = {aws_secret}\n"
        ),
        "~/.ssh/id_ed25519": (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            + "\n".join(ssh[i : i + 70] for i in range(0, len(ssh), 70))
            + "\n-----END OPENSSH PRIVATE KEY-----\n"
        ),
        "~/.config/gh/hosts.yml": f"github.com:\n    oauth_token: {gh}\n    user: dev\n",
        "~/.npmrc": f"//registry.npmjs.org/:_authToken={npm}\n",
        "./.env": f"OPENAI_API_KEY={openai}\nDATABASE_URL=postgres://app:{aws_secret[:16]}@db/app\n",
    }
    umgebung = {"OPENAI_API_KEY": openai, "GITHUB_TOKEN": gh, "AWS_ACCESS_KEY_ID": aws_id}
    werte = {
        aws_id: "AWS-Schlüssel",
        aws_secret: "AWS-Geheimnis",
        gh: "GitHub-Token",
        openai: "OpenAI-Schlüssel",
        npm: "npm-Token",
        ssh[:40]: "SSH-Schlüssel",
        aws_secret[:16]: "Datenbank-Passwort",
    }
    return KoederSatz(dateien, umgebung, werte)
