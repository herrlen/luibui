"""Alarm mails through the mittwald mailbox noreply@luibui.com (SMTP with STARTTLS).

Only status text: which check failed and since when. No user data, no secrets.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from luibui_ops.settings import Settings

log = logging.getLogger(__name__)
SMTP_TIMEOUT = 15


def senden(s: Settings, betreff: str, text: str) -> bool:
    """Send one alarm; False (and a log line) when mail is not set up or fails."""
    if not s.alarm_an or not s.smtp_password:
        log.warning("Alarm nicht versendet (ALARM_AN oder SMTP_PASSWORD fehlt): %s", betreff)
        return False
    m = EmailMessage()
    m["From"] = formataddr(("luibui Betrieb", s.smtp_user))
    m["To"] = s.alarm_an
    m["Subject"] = f"[luibui] {betreff}"
    m.set_content(text)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(m)
    except (OSError, smtplib.SMTPException) as exc:
        log.error("Alarm-Mail fehlgeschlagen (%s): %s", type(exc).__name__, betreff)
        return False
    log.info("Alarm versendet: %s", betreff)
    return True
