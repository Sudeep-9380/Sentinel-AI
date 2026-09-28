"""
Sentinel — SQLAlchemy Declarative Base & Shared Mixins.

Provides:
  - ``Base``              — Declarative base with a consistent naming convention.
  - ``TimestampMixin``    — Auto-managed ``created_at`` / ``updated_at`` columns.
  - ``SoftDeleteMixin``   — Nullable ``deleted_at`` for logical deletion.
  - ``generate_uuid``     — Default UUID4 generator for primary keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID4 value."""
    return uuid.uuid4()


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# ── Naming Convention ───────────────────────────────────────────
# Alembic uses these to generate deterministic constraint names.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


# ── Declarative Base ────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all Sentinel ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ── Mixins ──────────────────────────────────────────────────────
class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns with server defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Row creation timestamp (UTC).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp (UTC).",
    )


class SoftDeleteMixin:
    """Adds a nullable ``deleted_at`` column for logical (soft) deletion."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Soft-delete timestamp. NULL means the row is active.",
    )
