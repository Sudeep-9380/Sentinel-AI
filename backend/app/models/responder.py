"""
Sentinel — Responder Tier & Responder Models.

- ``ResponderTier``  — Hierarchy levels (T1 Security -> T4 Command).
- ``Responder``      — Individual authorized responders with GPS & FCM tokens.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid


class ResponderTier(Base, TimestampMixin):
    """Defines a tier in the escalation hierarchy (level 1=first responder, 4=command)."""

    __tablename__ = "responder_tiers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    responders = relationship("Responder", back_populates="tier", lazy="selectin")
    escalation_rules = relationship("EscalationRule", back_populates="responder_tier")

    def __repr__(self) -> str:
        return f"<ResponderTier(code={self.code!r}, level={self.level})>"


class Responder(Base, TimestampMixin, SoftDeleteMixin):
    """An individual authorized responder with GPS for Haversine proximity matching."""

    __tablename__ = "responders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    tier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("responder_tiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    fcm_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tier = relationship("ResponderTier", back_populates="responders")
    zone = relationship("Zone")
    notifications = relationship("NotificationLog", back_populates="responder")

    def __repr__(self) -> str:
        return f"<Responder(id={self.employee_id!r}, name={self.full_name!r})>"
