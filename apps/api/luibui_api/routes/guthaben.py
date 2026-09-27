"""Credits and purchases through PayPal (Len, 27.09.2026). See luibui_api.guthaben and .paypal."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text

from luibui_api import guthaben, paypal
from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, get_owned
from luibui_api.errors import fehler
from luibui_api.models import CreditEntry, Payment
from luibui_api.settings import get_settings

router = APIRouter(tags=["guthaben"])
_LOG = logging.getLogger("luibui.guthaben")


class PaketOut(BaseModel):
    id: str
    pruefungen: int
    preis_cent: int
    preis_text: str


class Kauf(BaseModel):
    id: uuid.UUID
    belegnummer: int | None
    pruefungen: int
    betrag_cent: int
    status: str
    bezahlt_am: datetime | None


class Guthaben(BaseModel):
    aktiv: bool
    """False while PayPal is not configured; then there are no limits."""
    stand: int
    email_bestaetigt: bool
    pakete: list[PaketOut]
    kaeufe: list[Kauf]


def _pakete() -> list[PaketOut]:
    return [
        PaketOut(id=p.id, pruefungen=p.pruefungen, preis_cent=p.preis_cent, preis_text=p.preis_text)
        for p in guthaben.PAKETE
    ]


@router.get("/api/v1/guthaben")
def stand(caller: CurrentCaller, db: DbSession) -> Guthaben:
    kaeufe = db.scalars(
        select(Payment)
        .where(Payment.owner_id == caller.user.id, Payment.status == "bezahlt")
        .order_by(Payment.bezahlt_am.desc())
    )
    return Guthaben(
        aktiv=guthaben.bezahlung_aktiv(),
        stand=guthaben.stand(db, caller.user.id),
        email_bestaetigt=caller.user.email_verified_at is not None,
        pakete=_pakete(),
        kaeufe=[
            Kauf(
                id=k.id,
                belegnummer=k.belegnummer,
                pruefungen=k.pruefungen,
                betrag_cent=k.betrag_cent,
                status=k.status,
                bezahlt_am=k.bezahlt_am,
            )
            for k in kaeufe
        ],
    )


class KaufNeu(BaseModel):
    paket: str = Field(max_length=20)
    zustimmung: bool
    """Consent that the service starts before the withdrawal period ends (§ 356 Abs. 5 BGB)."""
    kenntnis: bool
    """Confirmation that the right of withdrawal ends with the start of the service."""
    weiter: str = Field(default="/", max_length=200)

    @field_validator("weiter")
    @classmethod
    def _lokal(cls, value: str) -> str:
        # Only a path on app.luibui.com: no open redirect after the payment.
        if not value.startswith("/") or value.startswith("//") or "\\" in value:
            return "/"
        return value


class Weiterleitung(BaseModel):
    url: str


@router.post("/api/v1/guthaben/kaufen")
def kaufen(body: KaufNeu, caller: CurrentCaller, db: DbSession) -> Weiterleitung:
    guthaben.email_pruefen(caller.user)
    if not guthaben.bezahlung_aktiv():
        raise fehler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "bezahlung_aus",
            "Die Bezahlung ist noch nicht eingerichtet.",
        )
    paket = guthaben.PAKET.get(body.paket)
    if paket is None:
        raise fehler(status.HTTP_422_UNPROCESSABLE_CONTENT, "paket_unbekannt", "Unbekanntes Paket.")
    if not (body.zustimmung and body.kenntnis):
        raise fehler(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "zustimmung_fehlt",
            "Bitte bestätige beide Erklärungen zum Widerrufsrecht.",
        )
    basis = get_settings().app_origin
    weiter = quote(body.weiter, safe="/")
    try:
        order_id, url = paypal.bestellung_anlegen(
            paket.preis_cent,
            f"luibui: {paket.pruefungen} Prüfungen",
            str(caller.user.id),
            f"{basis}/guthaben/zurueck?weiter={weiter}",
            f"{basis}/guthaben/zurueck?abgebrochen=1&weiter={weiter}",
        )
    except paypal.PayPalError as exc:
        _LOG.warning("PayPal-Bestellung gescheitert: %s", exc)
        raise fehler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "paypal_fehler",
            "PayPal ist gerade nicht erreichbar. Bitte versuche es gleich noch einmal.",
        ) from None
    db.add(
        Payment(
            owner_id=caller.user.id,
            order_id=order_id,
            paket=paket.id,
            pruefungen=paket.pruefungen,
            betrag_cent=paket.preis_cent,
            kaeufer_email=caller.user.email,
        )
    )
    audit(db, caller.user.id, "guthaben.kauf_angelegt", "payment", None, paket=paket.id)
    db.commit()
    return Weiterleitung(url=url)


def gutschreiben(db: DbSession, order_id: str, owner_id: uuid.UUID | None) -> tuple[bool, int]:
    """Capture, check and credit exactly once. ``owner_id`` None: webhook (no session)."""
    zahlung = db.scalar(select(Payment).where(Payment.order_id == order_id))
    if zahlung is None or (owner_id is not None and zahlung.owner_id != owner_id):
        raise fehler(
            status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Diese Bestellung ist nicht bekannt."
        )
    if zahlung.status == "bezahlt" or zahlung.owner_id is None:
        return zahlung.status == "bezahlt", guthaben.stand(
            db, zahlung.owner_id
        ) if zahlung.owner_id else 0
    erwartet, kaeufer = zahlung.betrag_cent, zahlung.owner_id
    db.rollback()  # no lock while talking to PayPal
    try:
        antwort = paypal.erfassen(order_id)
    except paypal.PayPalError as exc:
        _LOG.warning("PayPal-Erfassung %s gescheitert: %s", order_id, exc)
        raise fehler(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "paypal_fehler",
            "PayPal ist gerade nicht erreichbar. Deine Zahlung geht nicht verloren, "
            "bitte lade die Seite gleich neu.",
        ) from None
    capture_id = paypal.bezahlt(antwort, erwartet)
    if capture_id is None:
        return False, guthaben.stand(db, kaeufer)
    zahlung = db.scalar(select(Payment).where(Payment.order_id == order_id).with_for_update())
    if zahlung is None or zahlung.status == "bezahlt":
        return True, guthaben.stand(db, kaeufer)
    zahlung.status = "bezahlt"
    zahlung.capture_id = capture_id or None
    zahlung.bezahlt_am = datetime.now(UTC)
    zahlung.belegnummer = int(db.scalar(text("SELECT nextval('belegnummer')")) or 0)
    db.add(
        CreditEntry(owner_id=kaeufer, delta=zahlung.pruefungen, grund="kauf", payment_id=zahlung.id)
    )
    audit(db, kaeufer, "guthaben.gekauft", "payment", zahlung.id, paket=zahlung.paket)
    db.commit()
    return True, guthaben.stand(db, kaeufer)


class Bestaetigung(BaseModel):
    order_id: str = Field(min_length=5, max_length=64, pattern=r"^[A-Za-z0-9-]+$")


class Ergebnis(BaseModel):
    bezahlt: bool
    stand: int


@router.post("/api/v1/guthaben/bestaetigen")
def bestaetigen(body: Bestaetigung, caller: CurrentCaller, db: DbSession) -> Ergebnis:
    bezahlt, neu = gutschreiben(db, body.order_id, caller.user.id)
    return Ergebnis(bezahlt=bezahlt, stand=neu)


@router.post("/api/v1/paypal/webhook", include_in_schema=False)
async def webhook(request: Request, db: DbSession) -> dict[str, bool]:
    """Safety net if the buyer never returns. Only signature-checked events count."""
    rumpf = await request.body()
    try:
        ereignis: dict[str, Any] = json.loads(rumpf)
    except ValueError:
        return {"verarbeitet": False}
    if not paypal.webhook_echt(dict(request.headers), ereignis):
        return {"verarbeitet": False}
    art = ereignis.get("event_type")
    quelle = ereignis.get("resource") or {}
    if art == "CHECKOUT.ORDER.APPROVED":
        order_id = quelle.get("id")
    elif art == "PAYMENT.CAPTURE.COMPLETED":
        order_id = ((quelle.get("supplementary_data") or {}).get("related_ids") or {}).get(
            "order_id"
        )
    else:
        return {"verarbeitet": False}
    if not isinstance(order_id, str):
        return {"verarbeitet": False}
    try:
        bezahlt, _ = gutschreiben(db, order_id, None)
    except Exception:
        return {"verarbeitet": False}
    return {"verarbeitet": bezahlt}


class Beleg(BaseModel):
    belegnummer: int
    datum: datetime
    kaeufer_email: str | None
    beschreibung: str
    betrag_cent: int
    waehrung: str
    paypal_transaktion: str | None


@router.get("/api/v1/guthaben/belege/{payment_id}")
def beleg(payment_id: uuid.UUID, caller: CurrentCaller, db: DbSession) -> Beleg:
    zahlung = get_owned(db, Payment, payment_id, caller)
    if zahlung.status != "bezahlt" or zahlung.belegnummer is None or zahlung.bezahlt_am is None:
        raise fehler(
            status.HTTP_404_NOT_FOUND, "nicht_gefunden", "Kein Beleg zu dieser Bestellung."
        )
    return Beleg(
        belegnummer=zahlung.belegnummer,
        datum=zahlung.bezahlt_am,
        kaeufer_email=zahlung.kaeufer_email,
        beschreibung=f"{zahlung.pruefungen} Prüfungen (Guthaben für luibui)",
        betrag_cent=zahlung.betrag_cent,
        waehrung=zahlung.waehrung,
        paypal_transaktion=zahlung.capture_id,
    )
