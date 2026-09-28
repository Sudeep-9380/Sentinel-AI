"""
Sentinel — Chain of Custody, Audit Log, and Playbook Models.

- ``ChainOfCustodyLog``   — Immutable, hash-chained ledger for legal evidence tracking.
- ``AuditLog``            — System-wide append-only audit trail.
- ``AutomatedPlaybook``   — Playbook definitions for automated response.
- ``PlaybookExecution``   — Runtime playbook execution records.

The ``ChainOfCustodyLog`` implements a SHA-256 hash-chain pattern:
each row stores ``prev_hash`` (the ``entry_hash`` of the previous row
for the same entity) and its own ``entry_hash`` computed from all
immutable fields.  A PostgreSQL trigger prevents UPDATE/DELETE.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, event
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.incident import Severity


# ── Enumerations ────────────────────────────────────────────────


class CustodyAction(str, enum.Enum):
    """Actions tracked in the chain of custody."""
    CREATED = "CREATED"
    HASHED = "HASHED"
    UPLOADED = "UPLOADED"
    ACCESSED = "ACCESSED"
    SHARED = "SHARED"
    SEALED = "SEALED"
    RETENTION_EXTENDED = "RETENTION_EXTENDED"
    DELETED = "DELETED"


class CustodyActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    RESPONDER = "RESPONDER"
    ADMIN = "ADMIN"
    LEGAL = "LEGAL"


class PlaybookStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AuditActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    RESPONDER = "RESPONDER"
    ADMIN = "ADMIN"
    API_CLIENT = "API_CLIENT"


# ── Chain of Custody Log ────────────────────────────────────────


class ChainOfCustodyLog(Base):
    """
    Immutable, append-only custody ledger with SHA-256 hash chaining.

    **Tamper detection**: each row's ``entry_hash`` is derived from its
    own fields plus ``prev_hash`` (the ``entry_hash`` of the preceding
    row for the same ``entity_id``).  Walking the chain backwards and
    re-computing hashes reveals any tampering.

    A PostgreSQL trigger (see ``scripts/immutability_triggers.sql``)
    blocks UPDATE and DELETE operations on this table at the database level.
    """

    __tablename__ = "chain_of_custody_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        doc="Type of entity, e.g. 'evidence_clip', 'incident'.",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        doc="1-based sequence within the entity's custody chain.",
    )
    action: Mapped[CustodyAction] = mapped_column(
        Enum(CustodyAction, name="custody_action_enum", create_constraint=True),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[CustodyActorType] = mapped_column(
        Enum(CustodyActorType, name="custody_actor_type_enum", create_constraint=True),
        nullable=False,
    )
    actor_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Hash of the entity's content at this point in time
    entity_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="SHA-256 hash of the entity content at time of this action.",
    )

    # Link to previous entry in the chain (NULL for the first entry)
    prev_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        doc="entry_hash of the previous custody log row for this entity.",
    )

    # Hash of THIS row's immutable fields — forms the chain link
    entry_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        doc="SHA-256 hash of this entry's canonical fields + prev_hash.",
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()",
    )

    # ── Hash-Chain Logic ────────────────────────────────────────

    @staticmethod
    def compute_entry_hash(
        entry_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        sequence_number: int,
        action: str,
        actor_id: uuid.UUID,
        actor_type: str,
        entity_hash: str,
        prev_hash: str | None,
        created_at: str,
    ) -> str:
        """
        Compute the SHA-256 hash for a custody log entry.

        The hash is derived from a canonical JSON representation of
        all immutable fields, ensuring deterministic re-computation
        for integrity verification.

        Returns:
            64-character lowercase hex digest.
        """
        canonical = json.dumps(
            {
                "id": str(entry_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "sequence_number": sequence_number,
                "action": action,
                "actor_id": str(actor_id),
                "actor_type": actor_type,
                "entity_hash": entity_hash,
                "prev_hash": prev_hash or "",
                "created_at": str(created_at),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def recompute_hash(self) -> str:
        """Recompute this entry's hash from its current field values."""
        return self.compute_entry_hash(
            entry_id=self.id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            sequence_number=self.sequence_number,
            action=self.action.value if isinstance(self.action, CustodyAction) else self.action,
            actor_id=self.actor_id,
            actor_type=self.actor_type.value if isinstance(self.actor_type, CustodyActorType) else self.actor_type,
            entity_hash=self.entity_hash,
            prev_hash=self.prev_hash,
            created_at=self.created_at,
        )

    def verify_integrity(self) -> bool:
        """Return True if entry_hash matches the recomputed hash."""
        return self.entry_hash == self.recompute_hash()

    def __repr__(self) -> str:
        return (
            f"<ChainOfCustodyLog(entity={self.entity_type}:{self.entity_id!s:.8}, "
            f"seq={self.sequence_number}, action={self.action.value})>"
        )


# ── SQLAlchemy Event: Auto-Compute entry_hash Before Insert ─────

@event.listens_for(ChainOfCustodyLog, "before_insert")
def _auto_compute_entry_hash(mapper, connection, target: ChainOfCustodyLog):
    """
    Automatically compute ``entry_hash`` before inserting a new row,
    if it has not already been set by the service layer.
    """
    if target.entry_hash:
        return  # Already set by caller

    if target.id is None:
        target.id = generate_uuid()
    if target.created_at is None:
        target.created_at = datetime.utcnow().isoformat()

    target.entry_hash = target.compute_entry_hash(
        entry_id=target.id,
        entity_type=target.entity_type,
        entity_id=target.entity_id,
        sequence_number=target.sequence_number,
        action=target.action.value if isinstance(target.action, CustodyAction) else target.action,
        actor_id=target.actor_id,
        actor_type=target.actor_type.value if isinstance(target.actor_type, CustodyActorType) else target.actor_type,
        entity_hash=target.entity_hash,
        prev_hash=target.prev_hash,
        created_at=target.created_at,
    )


# ── Audit Log ───────────────────────────────────────────────────


class AuditLog(Base):
    """
    System-wide audit log capturing all state-changing operations.
    Stores before/after JSON snapshots for forensic analysis.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(AuditActorType, name="audit_actor_type_enum", create_constraint=True), nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        doc="Dot-notation action, e.g. 'incident.created', 'escalation.triggered'.",
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action!r}, entity={self.entity_type}:{self.entity_id!s:.8})>"


# ── Automated Playbooks ─────────────────────────────────────────


class AutomatedPlaybook(Base, TimestampMixin):
    """Defines an automated response playbook triggered by incident conditions."""

    __tablename__ = "automated_playbooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    threat_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threat_types.id", ondelete="SET NULL"), nullable=True,
    )
    min_severity: Mapped[Severity | None] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=True), nullable=True,
    )
    steps: Mapped[dict] = mapped_column(
        JSON, nullable=False, doc="Ordered list of playbook action steps.",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    executions = relationship("PlaybookExecution", back_populates="playbook")

    def __repr__(self) -> str:
        return f"<AutomatedPlaybook(name={self.name!r}, v{self.version})>"


class PlaybookExecution(Base):
    """Runtime execution record of a playbook against an incident."""

    __tablename__ = "playbook_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    playbook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automated_playbooks.id", ondelete="CASCADE"), nullable=False,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    status: Mapped[PlaybookStatus] = mapped_column(
        Enum(PlaybookStatus, name="playbook_status_enum", create_constraint=True),
        nullable=False, default=PlaybookStatus.RUNNING,
    )
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    steps_completed: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    playbook = relationship("AutomatedPlaybook", back_populates="executions")
    incident = relationship("Incident", back_populates="playbook_executions")

    def __repr__(self) -> str:
        return f"<PlaybookExecution(playbook={self.playbook_id!s:.8}, status={self.status.value})>"
