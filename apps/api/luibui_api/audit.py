"""Audit log: metadata only (who, what, which resource). Never contents, findings or secrets."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from luibui_api.models import AuditLog


def audit(
    db: Session,
    actor_id: uuid.UUID | None,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    **meta: Any,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            meta=meta,
        )
    )
