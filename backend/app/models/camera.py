"""
Sentinel — Camera Model.

Represents a physical camera feed source with RTSP connection details,
resolution metadata, and zone assignment.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid



class CameraType(str, enum.Enum):
    """Physical camera classification."""

    FIXED = "FIXED"
    PTZ = "PTZ"  # Pan-Tilt-Zoom
    THERMAL = "THERMAL"
    DOME = "DOME"
    BULLET = "BULLET"


class CameraStatus(str, enum.Enum):
    """Operational status of a camera."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"


class Camera(Base, TimestampMixin, SoftDeleteMixin):
    """A single camera feed source linked to a monitored zone."""

    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    rtsp_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    camera_type: Mapped[CameraType] = mapped_column(
        Enum(CameraType, name="camera_type_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[CameraStatus] = mapped_column(
        Enum(CameraStatus, name="camera_status_enum", create_constraint=True),
        nullable=False,
        default=CameraStatus.OFFLINE,
    )

    # Zone assignment
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Physical location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Stream metadata
    resolution_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    resolution_height: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)
    fps: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ───────────────────────────────────────────
    zone = relationship("Zone", back_populates="cameras")
    incidents = relationship("Incident", back_populates="camera", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Camera(id={self.id!s:.8}, name={self.name!r}, status={self.status.value})>"
