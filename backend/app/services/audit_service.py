"""
Sentinel — Audit Service.

System-wide audit logging that captures before/after state snapshots
for any entity mutation.  All entries are append-only (enforced by
the ``trg_audit_log_immutable`` PostgreSQL trigger).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditActorType, AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for recording system-wide audit events."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        *,
        actor_id: uuid.UUID | None = None,
        actor_type: AuditActorType = AuditActorType.SYSTEM,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """
        Append an audit log entry.

        Args:
            action:       Dot-notation action string, e.g. ``"incident.created"``.
            entity_type:  Type of the affected entity, e.g. ``"incident"``.
            entity_id:    UUID of the affected entity.
            actor_id:     UUID of the actor (None for system-initiated actions).
            actor_type:   Classification of the actor.
            before_state: JSON-serialisable snapshot before the change.
            after_state:  JSON-serialisable snapshot after the change.
            ip_address:   Optional client IP address.
            user_agent:   Optional client User-Agent string.

        Returns:
            The newly created ``AuditLog`` row.
        """
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(entry)
        await self._db.flush()

        logger.info(
            "Audit: %s on %s:%s by %s(%s)",
            action, entity_type, entity_id,
            actor_type.value, actor_id or "system",
        )
        return entry
