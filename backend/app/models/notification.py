"""
Sentinel — Notification Log Model.

Append-only log of every notification dispatched through FCM, SMS, or Voice channels.
Records delivery status and provider message IDs for auditability.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class NotificationChannel(str, enum.Enum):
    FCM = "FCM"
    SMS = "SMS"
    VOICE = "VOICE"
    EMAIL = "EMAIL"


class NotificationStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class NotificationLog(Base):
    """Immutable record of a notification sent to a responder."""

    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    escalation_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escalation_actions.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("responders.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel_enum", create_constraint=True), nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status_enum", create_constraint=True),
        nullable=False, default=NotificationStatus.QUEUED,
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="Twilio SID or FCM message ID.",
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sent_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    responder = relationship("Responder", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<NotificationLog(channel={self.channel.value}, status={self.status.value})>"
