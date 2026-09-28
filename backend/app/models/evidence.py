"""
Sentinel — Evidence Models.

- ``EvidenceClip``           — S3-hosted video clip with SHA-256 hash and retention policy.
- ``EvidenceClipAccessLog``  — Append-only log of every access to evidence.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class EvidenceStatus(str, enum.Enum):
    RECORDING = "RECORDING"
    UPLOADING = "UPLOADING"
    AVAILABLE = "AVAILABLE"
    SEALED = "SEALED"
    DELETED = "DELETED"


class EvidenceAccessAction(str, enum.Enum):
    VIEWED = "VIEWED"
    DOWNLOADED = "DOWNLOADED"
    SHARED = "SHARED"
    EXPORTED = "EXPORTED"


class ActorType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    RESPONDER = "RESPONDER"
    ADMIN = "ADMIN"
    LEGAL = "LEGAL"


class EvidenceClip(Base, TimestampMixin):
    """S3-hosted evidence video clip with SHA-256 integrity hash and retention policy."""

    __tablename__ = "evidence_clips"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False,
    )
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    pre_event_buffer_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    post_event_buffer_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    encryption_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False, default="video/mp4")
    retention_expires_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        doc="When set, evidence is eligible for automated purging after this time.",
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status_enum", create_constraint=True),
        nullable=False, default=EvidenceStatus.RECORDING,
    )

    # Relationships
    incident = relationship("Incident", back_populates="evidence_clips")
    camera = relationship("Camera")
    access_logs = relationship("EvidenceClipAccessLog", back_populates="evidence_clip", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<EvidenceClip(id={self.id!s:.8}, status={self.status.value})>"


class EvidenceClipAccessLog(Base):
    """Append-only log recording every access to an evidence clip."""

    __tablename__ = "evidence_clip_access_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    evidence_clip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_clips.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type_enum", create_constraint=True), nullable=False,
    )
    action: Mapped[EvidenceAccessAction] = mapped_column(
        Enum(EvidenceAccessAction, name="evidence_access_action_enum", create_constraint=True), nullable=False,
    )
    actor_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    evidence_clip = relationship("EvidenceClip", back_populates="access_logs")

    def __repr__(self) -> str:
        return f"<EvidenceClipAccessLog(clip={self.evidence_clip_id!s:.8}, action={self.action.value})>"
