"""Namespaces, the ``org`` in ``org/paket`` (S4-1). Several per account; names are checked
against reserved names and look-alikes of existing ones (Prüfkatalog H04, ``register.py``)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from luibui_api.audit import audit
from luibui_api.auth import CurrentCaller, DbSession, SessionCaller, get_owned
from luibui_api.errors import fehler
from luibui_api.models import Namespace
from luibui_api.register import RESERVIERT, name_fehler, verwechslung

router = APIRouter(prefix="/api/v1/namespaces", tags=["register"])

MAX_JE_KONTO = 5


class NamespaceNeu(BaseModel):
    name: str = Field(max_length=39)


class NamespaceInfo(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


def _info(n: Namespace) -> NamespaceInfo:
    return NamespaceInfo(id=n.id, name=n.name, created_at=n.created_at)


@router.get("")
def liste(caller: CurrentCaller, db: DbSession) -> list[NamespaceInfo]:
    rows = db.scalars(
        select(Namespace).where(Namespace.owner_id == caller.user.id).order_by(Namespace.name)
    )
    return [_info(n) for n in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def anlegen(body: NamespaceNeu, caller: SessionCaller, db: DbSession) -> NamespaceInfo:
    name = body.name.strip().lower()
    if grund := name_fehler(name):
        raise fehler(status.HTTP_422_UNPROCESSABLE_CONTENT, "name_ungueltig", grund)
    eigene = db.scalar(
        select(func.count()).select_from(Namespace).where(Namespace.owner_id == caller.user.id)
    )
    if (eigene or 0) >= MAX_JE_KONTO:
        raise fehler(
            status.HTTP_409_CONFLICT,
            "zu_viele",
            f"Höchstens {MAX_JE_KONTO} Namespaces je Konto.",
        )
    fremde = db.scalars(select(Namespace.name).where(Namespace.owner_id != caller.user.id))
    eigene_namen = set(
        db.scalars(select(Namespace.name).where(Namespace.owner_id == caller.user.id))
    )
    if name in eigene_namen:
        raise fehler(status.HTTP_409_CONFLICT, "vergeben", "Diesen Namespace hast du schon.")
    if aehnlich := verwechslung(name, fremde):
        text = (
            "Dieser Name ist reserviert oder zu nah an einem geschützten Namen."
            if aehnlich in RESERVIERT
            else "Dieser Name ist vergeben oder lässt sich mit einem vergebenen verwechseln."
        )
        raise fehler(status.HTTP_409_CONFLICT, "verwechselbar", text)
    ns = Namespace(owner_id=caller.user.id, name=name)
    db.add(ns)
    try:
        db.flush()
    except IntegrityError:  # registered in the same moment by someone else
        db.rollback()
        raise fehler(
            status.HTTP_409_CONFLICT,
            "verwechselbar",
            "Dieser Name ist vergeben oder lässt sich mit einem vergebenen verwechseln.",
        ) from None
    db.refresh(ns)
    audit(db, caller.user.id, "namespace.angelegt", "namespace", ns.id)
    db.commit()
    return _info(ns)


@router.delete("/{namespace_id}", status_code=status.HTTP_204_NO_CONTENT)
def loeschen(namespace_id: uuid.UUID, caller: SessionCaller, db: DbSession) -> None:
    """Only while it holds no published package (S4-2 keeps packages from being orphaned)."""
    ns = get_owned(db, Namespace, namespace_id, caller)
    db.delete(ns)
    audit(db, caller.user.id, "namespace.geloescht", "namespace", namespace_id)
    db.commit()
