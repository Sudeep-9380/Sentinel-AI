"""
Sentinel — Zone Model.

Represents a monitored geographic zone (building, floor, perimeter, etc.).
Supports hierarchical zones via self-referential ``parent_zone_id``.
GPS coordinates stored as simple floats (Haversine distance at application layer).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid


class ZoneType(str, enum.Enum):
    """Classification of monitored zones."""

    BUILDING = "BUILDING"
    FLOOR = "FLOOR"
    PERIMETER = "PERIMETER"
    PARKING = "PARKING"
    OUTDOOR = "OUTDOOR"
    ENTRANCE = "ENTRANCE"
    RESTRICTED = "RESTRICTED"


class Zone(Base, TimestampMixin, SoftDeleteMixin):
    """A monitored geographic zone with optional polygon boundary."""

    __tablename__ = "zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_type: Mapped[ZoneType] = mapped_column(
        Enum(ZoneType, name="zone_type_enum", create_constraint=True),
        nullable=False,
    )

    # GPS centroid of the zone
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Polygon boundary — stored as JSON array of {lat, lng} points.
    # No PostGIS; Haversine computed at application layer.
    boundary_polygon: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Self-referential hierarchy (e.g. Building → Floor → Room)
    parent_zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Relationships ───────────────────────────────────────────
    parent_zone = relationship("Zone", remote_side="Zone.id", back_populates="child_zones")
    child_zones = relationship("Zone", back_populates="parent_zone", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="zone", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Zone(id={self.id!s:.8}, name={self.name!r}, type={self.zone_type.value})>"
