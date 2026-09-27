"""Credits: who may start a check or create a project (Konzept, Len 27.09.2026).

Free: one project and three checks (start credit, given once the e-mail is confirmed). Every
further check costs one credit, in a project or as a single check; more projects need a
purchase. Credits come as packages through PayPal. Without PayPal credentials the limits are off:
nobody may run into a paywall they cannot pay.
"""

import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from luibui_api.errors import fehler
from luibui_api.models import CreditEntry, Payment, Project, User
from luibui_api.settings import get_settings

STARTGUTHABEN = 3


@dataclass(frozen=True, slots=True)
class Paket:
    id: str
    pruefungen: int
    preis_cent: int

    @property
    def preis_text(self) -> str:
        return f"{self.preis_cent // 100},{self.preis_cent % 100:02d} €"


PAKETE = (Paket("p10", 10, 490), Paket("p25", 25, 990))
PAKET = {p.id: p for p in PAKETE}


def bezahlung_aktiv() -> bool:
    s = get_settings()
    return bool(s.paypal_client_id and s.paypal_secret and s.paypal_secret.get_secret_value())


def stand(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(CreditEntry.delta), 0)).where(
                CreditEntry.owner_id == user_id
            )
        )
        or 0
    )


def hat_gekauft(db: Session, user_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(Payment.id)
            .where(Payment.owner_id == user_id, Payment.status == "bezahlt")
            .limit(1)
        )
        is not None
    )


def startguthaben(db: Session, user: User) -> None:
    """Once per account; the partial unique index makes a second call a no-op."""
    db.execute(
        insert(CreditEntry)
        .values(owner_id=user.id, delta=STARTGUTHABEN, grund="start")
        .on_conflict_do_nothing(
            index_elements=["owner_id"], index_where=CreditEntry.grund == "start"
        )
    )


def email_pruefen(user: User) -> None:
    if get_settings().email_bestaetigung_pflicht and user.email_verified_at is None:
        raise fehler(
            status.HTTP_403_FORBIDDEN,
            "email_unbestaetigt",
            "Bitte bestätige zuerst deine E-Mail-Adresse. Den Link haben wir dir geschickt.",
        )


def _gesperrt(db: Session, user: User) -> None:
    # Serialises checks and purchases of one account: no two requests spend the last credit.
    db.execute(select(User.id).where(User.id == user.id).with_for_update())


def pruefung_abbuchen(db: Session, user: User) -> CreditEntry | None:
    """Book one credit for a check in the current transaction, or answer 402."""
    email_pruefen(user)
    if not bezahlung_aktiv():
        return None
    _gesperrt(db, user)
    if stand(db, user.id) < 1:
        raise zahlung_noetig("guthaben_leer", "Dein Guthaben ist aufgebraucht.")
    entry = CreditEntry(owner_id=user.id, delta=-1, grund="pruefung")
    db.add(entry)
    db.flush()
    return entry


def projekt_erlaubt(db: Session, user: User) -> None:
    if not bezahlung_aktiv():
        return
    anzahl = db.scalar(select(func.count()).select_from(Project).where(Project.owner_id == user.id))
    if int(anzahl or 0) >= 1 and not hat_gekauft(db, user.id):
        raise zahlung_noetig(
            "projekt_limit", "Gratis ist ein Projekt. Für weitere Projekte lade bitte Guthaben auf."
        )


def zahlung_noetig(code: str, text: str) -> HTTPException:
    return fehler(
        status.HTTP_402_PAYMENT_REQUIRED,
        code,
        text,
        pakete=[
            {"id": p.id, "pruefungen": p.pruefungen, "preis_cent": p.preis_cent} for p in PAKETE
        ],
    )
