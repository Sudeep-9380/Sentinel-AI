"""
Sentinel — Incident & Detection Models.

- ``ThreatType``          — Enumeration of detectable anomaly categories.
- ``Incident``            — Core event raised by the AI pipeline.
- ``IncidentDetection``   — Per-frame AI inference results (bounding boxes,
                            skeleton keypoints, heatmap URIs).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid


# ── Enumerations ────────────────────────────────────────────────


class Severity(str, enum.Enum):
    """Incident severity tier."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, enum.Enum):
    """Lifecycle status of an incident."""

    DETECTED = "DETECTED"
    ESCALATED = "ESCALATED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FALSE_ALARM = "FALSE_ALARM"
    CLOSED = "CLOSED"


# ── ThreatType ──────────────────────────────────────────────────


class ThreatType(Base, TimestampMixin):
    """
    Lookup table for detectable threat categories.

    Acts as an enum-like reference table so new threat types can be
    added at runtime without schema migrations.
    """

    __tablename__ = "threat_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        doc="Machine-readable code, e.g. 'VIOLENCE', 'FIRE_SMOKE'.",
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False,
        doc="Human-readable display name.",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=True),
        nullable=False,
        default=Severity.HIGH,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ───────────────────────────────────────────
    incidents = relationship("Incident", back_populates="threat_type")
    escalation_rules = relationship("EscalationRule", back_populates="threat_type")

    def __repr__(self) -> str:
        return f"<ThreatType(code={self.code!r})>"


# ── Incident ────────────────────────────────────────────────────


class Incident(Base, TimestampMixin, SoftDeleteMixin):
    """
    Core incident record created when the AI pipeline detects an anomaly.

    Each incident is linked to a camera, zone, and threat type, and
    carries the AI model's confidence score and severity assessment.
    """

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    incident_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
        doc="Human-readable incident ID, e.g. 'INC-20260425-0001'.",
    )

    # Foreign keys
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    threat_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threat_types.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    # AI assessment
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status_enum", create_constraint=True),
        nullable=False,
        default=IncidentStatus.DETECTED,
    )
    ai_confidence: Mapped[float] = mapped_column(
        Float, nullable=False,
        doc="AI model confidence score in [0.0, 1.0].",
    )
    ai_model_version: Mapped[str] = mapped_column(
        String(64), nullable=False,
        doc="Identifier of the AI model/version that produced this detection.",
    )

    # Timestamps
    detected_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False,
        doc="Exact timestamp of the initial detection.",
    )
    resolved_at: Mapped[str | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # GPS of the detection (from camera position)
    gps_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    gps_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Operator notes / AI summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Saved evidence image
    evidence_path: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        doc="Path to the saved evidence image."
    )

    # Auto-dispatched offices metadata
    dispatched_offices: Mapped[list[dict] | None] = mapped_column(
        JSON, nullable=True,
        doc="List of the 3 nearest dispatched emergency offices with distances."
    )

    # ── Relationships ───────────────────────────────────────────
    camera = relationship("Camera", back_populates="incidents")
    zone = relationship("Zone")
    threat_type = relationship("ThreatType", back_populates="incidents")
    detections = relationship(
        "IncidentDetection", back_populates="incident",
        cascade="all, delete-orphan", lazy="selectin",
    )
    escalation_actions = relationship(
        "EscalationAction", back_populates="incident",
        cascade="all, delete-orphan", lazy="selectin",
    )
    evidence_clips = relationship(
        "EvidenceClip", back_populates="incident",
        cascade="all, delete-orphan", lazy="selectin",
    )
    acknowledgements = relationship(
        "IncidentAcknowledgement", back_populates="incident",
        cascade="all, delete-orphan",
    )
    playbook_executions = relationship(
        "PlaybookExecution", back_populates="incident",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Incident(number={self.incident_number!r}, "
            f"severity={self.severity.value}, status={self.status.value})>"
        )


# ── IncidentDetection ───────────────────────────────────────────


class IncidentDetection(Base):
    """
    Per-frame AI inference results for an incident.

    Stores bounding boxes, skeleton keypoints, heatmap overlay URIs,
    and model performance metadata. Created at high frequency during
    an active incident.
    """

    __tablename__ = "incident_detections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    frame_number: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    # Detection payloads (JSON for flexibility across model outputs)
    bounding_boxes: Mapped[dict] = mapped_column(
        JSON, nullable=False,
        doc='List of {x, y, w, h, label, confidence} detections.',
    )
    skeleton_keypoints: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        doc="Skeletal tracking keypoints for pose estimation.",
    )
    heatmap_uri: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        doc="S3/local URI to the XAI heatmap overlay image.",
    )
    raw_frame_uri: Mapped[str | None] = mapped_column(
        String(1024), nullable=True,
        doc="S3/local URI to the raw captured frame.",
    )

    ai_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    inference_time_ms: Mapped[float] = mapped_column(
        Float, nullable=False,
        doc="Model inference latency in milliseconds.",
    )

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), nullable=False,
        server_default="now()",
    )

    # ── Relationships ───────────────────────────────────────────
    incident = relationship("Incident", back_populates="detections")

    def __repr__(self) -> str:
        return f"<IncidentDetection(incident={self.incident_id!s:.8}, frame={self.frame_number})>"
