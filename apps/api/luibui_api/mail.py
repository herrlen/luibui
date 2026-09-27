"""Sending mail through the mittwald mailbox noreply@luibui.com (SMTP with STARTTLS).

Only plain-text mails: the confirmation link and the contact form. Nothing is logged about the
content or the recipient.
"""

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from luibui_api.settings import get_settings

SMTP_TIMEOUT = 15


class MailError(OSError):
    """Mail could not be sent (not configured, connection or login failed)."""


def senden(
    an: str, betreff: str, text: str, *, absender_name: str = "luibui", reply_to: str | None = None
) -> None:
    s = get_settings()
    if s.smtp_password is None or not s.smtp_password.get_secret_value():
        raise MailError("SMTP nicht eingerichtet")
    m = EmailMessage()
    m["From"] = formataddr((absender_name, s.smtp_user))
    m["To"] = an
    if reply_to:
        m["Reply-To"] = reply_to
    m["Subject"] = betreff
    m.set_content(text)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=SMTP_TIMEOUT) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(s.smtp_user, s.smtp_password.get_secret_value())
            smtp.send_message(m)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailError(type(exc).__name__) from None
