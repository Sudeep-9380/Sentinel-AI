"""
Sentinel — Escalation Matrix Models.

- ``EscalationRule``             — Maps threat_type + severity to a responder tier + SLA.
- ``EscalationAction``           — Runtime escalation instance tied to an incident.
- ``IncidentAcknowledgement``    — Record of who acknowledged an incident and when.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.incident import Severity


class EscalationStatus(str, enum.Enum):
    """Runtime status of an escalation action."""
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED = "ESCALATED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class EscalationRule(Base, TimestampMixin):
    """
    Matrix rule: threat_type + min_severity -> responder_tier + SLA.

    The escalation engine queries these rules in ``priority_order`` to
    determine which tier to notify first for a given incident.
    """

    __tablename__ = "escalation_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    threat_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threat_types.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    min_severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", create_constraint=True), nullable=False,
    )
    responder_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responder_tiers.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    sla_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True,
    )
    priority_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        doc="Lower value = tried first within the same threat/severity combo.",
    )
    notification_channels: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: ["FCM", "SMS"],
        doc='Ordered list of channels, e.g. ["FCM", "SMS", "VOICE"].',
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    threat_type = relationship("ThreatType", back_populates="escalation_rules")
    responder_tier = relationship("ResponderTier", back_populates="escalation_rules")
    zone = relationship("Zone")
    escalation_actions = relationship("EscalationAction", back_populates="escalation_rule")

    def __repr__(self) -> str:
        return f"<EscalationRule(name={self.name!r}, priority={self.priority_order})>"


class EscalationAction(Base, TimestampMixin):
    """
    A runtime escalation instance created when an incident triggers a rule.

    Tracks dispatch time, acknowledgement, timeout, and Celery task ID
    for the 60-second secondary-escalation countdown.
    """

    __tablename__ = "escalation_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    escalation_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escalation_rules.id", ondelete="CASCADE"), nullable=False,
    )
    responder_tier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responder_tiers.id", ondelete="CASCADE"), nullable=False,
    )
    status: Mapped[EscalationStatus] = mapped_column(
        Enum(EscalationStatus, name="escalation_status_enum", create_constraint=True),
        nullable=False, default=EscalationStatus.PENDING,
    )
    dispatched_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responders.id", ondelete="SET NULL"), nullable=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    incident = relationship("Incident", back_populates="escalation_actions")
    escalation_rule = relationship("EscalationRule", back_populates="escalation_actions")
    responder_tier = relationship("ResponderTier")
    acknowledged_by = relationship("Responder")

    def __repr__(self) -> str:
        return f"<EscalationAction(incident={self.incident_id!s:.8}, status={self.status.value})>"


class IncidentAcknowledgement(Base):
    """
    Immutable record capturing exactly who acknowledged an incident,
    from which device, and their GPS position at the time.
    """

    __tablename__ = "incident_acknowledgements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    escalation_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escalation_actions.id", ondelete="CASCADE"), nullable=False,
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responders.id", ondelete="CASCADE"), nullable=False,
    )
    acknowledged_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    incident = relationship("Incident", back_populates="acknowledgements")
    escalation_action = relationship("EscalationAction")
    responder = relationship("Responder")

    def __repr__(self) -> str:
        return f"<IncidentAcknowledgement(incident={self.incident_id!s:.8})>"
