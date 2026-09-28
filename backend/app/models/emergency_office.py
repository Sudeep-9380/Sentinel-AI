"""
Sentinel — Emergency Office Model.

- ``EmergencyOffice`` — A responder location (Fire Station, Police Station, Hospital).
"""

from __future__ import annotations

import uuid

from sqlalchemy import String, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class EmergencyOffice(Base, TimestampMixin):
    """
    Physical location of an emergency responder office.
    Used for dispatching the nearest responders.
    """

    __tablename__ = "emergency_offices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    office_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
        doc="e.g., 'FIRE', 'POLICE', 'HOSPITAL'"
    )
    
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    contact_number: Mapped[str] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<EmergencyOffice(name={self.name!r}, type={self.office_type!r})>"
