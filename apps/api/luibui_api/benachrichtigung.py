"""Mails to account holders and their settings (S5-9).

Every kind is on unless the account switched it off. A mail that cannot be sent is logged and
never fails the action that caused it.
"""

import logging

from luibui_api import mail
from luibui_api.models import User

log = logging.getLogger(__name__)

ARTEN: dict[str, str] = {
    "nachpruefung": "Neue Befunde in meinen veröffentlichten Paketen (nächtliche Nachprüfung)",
    "einspruch": "Entscheidung der Moderation über meine Einsprüche",
}
FUSS = "\n\n-- \nluibui · luibui.com · Benachrichtigungen ändern: Konto → Benachrichtigungen.\n"


def einstellungen(user: User) -> dict[str, bool]:
    gespeichert = user.benachrichtigungen if isinstance(user.benachrichtigungen, dict) else {}
    return {art: gespeichert.get(art) is not False for art in ARTEN}


def senden(user: User, art: str, betreff: str, text: str) -> bool:
    """True if a mail went out. Respects the account's setting for ``art``."""
    if not einstellungen(user).get(art, True):
        return False
    try:
        mail.senden(user.email, betreff, text.rstrip() + FUSS)
    except mail.MailError:
        log.warning("mail of kind %s could not be sent", art)
        return False
    return True
