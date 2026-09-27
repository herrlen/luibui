"""PayPal Orders API v2, server side only (after websecureaudit/bezahlung.py).

No PayPal script is loaded in the browser (no external resources, CLAUDE.md). The flow:
create an order here, send the buyer to PayPal, and capture the order when they come back. The
capture result is checked against what we ordered (amount, currency, status) before anything is
credited, so a manipulated or foreign order unlocks nothing. Crediting happens exactly once:
the transition ``angelegt → bezahlt`` under a row lock is the latch; return and webhook may both
arrive.
"""

import base64
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from luibui_api.settings import get_settings

WAEHRUNG = "EUR"
ZEITLIMIT = 15.0

_token: str | None = None
_token_bis = 0.0
_sperre = threading.Lock()


class PayPalError(RuntimeError):
    """PayPal unreachable or refused; the page shows a calm message, details go to the log."""


def _basis() -> str:
    if get_settings().paypal_modus.lower() == "sandbox":
        return "https://api-m.sandbox.paypal.com"
    return "https://api-m.paypal.com"


def _abrufen(pfad: str, daten: dict[str, Any] | None, methode: str, kopf: dict[str, str]) -> Any:
    rumpf = json.dumps(daten).encode() if daten is not None else None
    anfrage = urllib.request.Request(  # noqa: S310 - fixed https base URL
        _basis() + pfad,
        data=rumpf,
        headers={"Content-Type": "application/json", **kopf},
        method=methode,
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:  # noqa: S310
            roh = antwort.read().decode()
    except urllib.error.HTTPError as exc:
        raise PayPalError(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:300]}"
        ) from None
    except OSError as exc:
        raise PayPalError(f"nicht erreichbar: {type(exc).__name__}") from None
    return json.loads(roh) if roh else {}


def _zugangstoken() -> str:
    global _token, _token_bis
    with _sperre:
        if _token and time.time() < _token_bis:
            return _token
        s = get_settings()
        secret = s.paypal_secret.get_secret_value() if s.paypal_secret else ""
        ausweis = base64.b64encode(f"{s.paypal_client_id}:{secret}".encode()).decode()
        anfrage = urllib.request.Request(  # noqa: S310
            _basis() + "/v1/oauth2/token",
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {ausweis}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:  # noqa: S310
                daten = json.loads(antwort.read().decode())
        except (OSError, ValueError) as exc:
            raise PayPalError(f"Anmeldung scheiterte: {type(exc).__name__}") from None
        _token = str(daten["access_token"])
        _token_bis = time.time() + max(int(daten.get("expires_in", 0)) - 60, 0)
        return _token


def aufrufen(pfad: str, daten: dict[str, Any] | None = None, methode: str = "POST") -> Any:
    return _abrufen(pfad, daten, methode, {"Authorization": f"Bearer {_zugangstoken()}"})


def bestellung_anlegen(
    betrag_cent: int, beschreibung: str, referenz: str, rueckkehr: str, abbruch: str
) -> tuple[str, str]:
    """Create an order; return (order id, URL where the buyer approves it)."""
    antwort = aufrufen(
        "/v2/checkout/orders",
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": WAEHRUNG,
                        "value": f"{betrag_cent // 100}.{betrag_cent % 100:02d}",
                    },
                    "description": beschreibung[:127],
                    "custom_id": referenz[:127],
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": rueckkehr,
                        "cancel_url": abbruch,
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                        "brand_name": "luibui",
                        "locale": "de-DE",
                    }
                }
            },
        },
    )
    order_id = antwort.get("id")
    link = next(
        (
            x["href"]
            for x in antwort.get("links", [])
            if x.get("rel") in ("payer-action", "approve")
        ),
        None,
    )
    if not order_id or not link:
        raise PayPalError("Bestellung ohne Nummer oder Zahlungsadresse")
    return str(order_id), str(link)


def erfassen(order_id: str) -> dict[str, Any]:
    """Capture the order; an order captured before is read instead of failing."""
    try:
        antwort = aufrufen(f"/v2/checkout/orders/{order_id}/capture", {})
    except PayPalError:
        antwort = {}
    if antwort.get("status") != "COMPLETED":
        antwort = aufrufen(f"/v2/checkout/orders/{order_id}", methode="GET")
    return dict(antwort)


def bezahlt(antwort: dict[str, Any], erwartet_cent: int) -> str | None:
    """The capture id if exactly what we ordered was paid, else None."""
    if antwort.get("status") != "COMPLETED":
        return None
    for einheit in antwort.get("purchase_units", []):
        for erfassung in (einheit.get("payments") or {}).get("captures", []):
            betrag = erfassung.get("amount") or {}
            if betrag.get("currency_code") != WAEHRUNG or erfassung.get("status") != "COMPLETED":
                continue
            try:
                cent = round(float(betrag.get("value", "0")) * 100)
            except (TypeError, ValueError):
                continue
            if cent == erwartet_cent:
                return str(erfassung.get("id") or "")
    return None


def webhook_echt(kopf: dict[str, str], ereignis: dict[str, Any]) -> bool:
    """Let PayPal confirm the signature. Without a webhook id nothing is trusted."""
    webhook_id = get_settings().paypal_webhook_id
    if not webhook_id:
        return False
    k = {name.lower(): wert for name, wert in kopf.items()}
    try:
        antwort = aufrufen(
            "/v1/notifications/verify-webhook-signature",
            {
                "auth_algo": k.get("paypal-auth-algo", ""),
                "cert_url": k.get("paypal-cert-url", ""),
                "transmission_id": k.get("paypal-transmission-id", ""),
                "transmission_sig": k.get("paypal-transmission-sig", ""),
                "transmission_time": k.get("paypal-transmission-time", ""),
                "webhook_id": webhook_id,
                "webhook_event": ereignis,
            },
        )
    except PayPalError:
        return False
    return bool(antwort.get("verification_status") == "SUCCESS")
