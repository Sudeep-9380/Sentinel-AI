"""
Sentinel — Chain of Custody Service.

Provides an append-only, hash-chained evidence custody ledger.

Every state-changing operation on a tracked entity (evidence clips,
incidents) is recorded as a new row in ``chain_of_custody_log`` with:

  - ``prev_hash`` — the ``entry_hash`` of the preceding row (per entity)
  - ``entry_hash`` — SHA-256 of this row's canonical fields + prev_hash

This forms a tamper-evident linked list.  The ``verify_chain()`` method
walks the chain and re-computes every hash to detect modification.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import (
    ChainOfCustodyLog,
    CustodyAction,
    CustodyActorType,
)

logger = logging.getLogger(__name__)


class ChainOfCustodyService:
    """Service for managing the legally-defensible chain of custody."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Public API ──────────────────────────────────────────────

    async def log_event(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: CustodyAction,
        actor_id: uuid.UUID,
        actor_type: CustodyActorType,
        entity_hash: str,
        *,
        actor_ip: str | None = None,
        device_fingerprint: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChainOfCustodyLog:
        """
        Append a new entry to the custody chain for an entity.

        Automatically resolves ``prev_hash`` from the most recent
        existing entry for the same ``entity_id`` and computes the
        new ``entry_hash``.

        Args:
            entity_type: Type label, e.g. ``"evidence_clip"``, ``"incident"``.
            entity_id:   UUID of the tracked entity.
            action:      The custody action being recorded.
            actor_id:    UUID of the user/system performing the action.
            actor_type:  Classification of the actor.
            entity_hash: SHA-256 of the entity's content at this point.
            actor_ip:    Optional IP address of the actor.
            device_fingerprint: Optional device identifier.
            metadata:    Optional JSON-serialisable metadata dict.

        Returns:
            The newly created ``ChainOfCustodyLog`` row.
        """
        # 1. Resolve the previous entry for this entity
        prev_entry = await self._get_latest_entry(entity_id)
        prev_hash = prev_entry.entry_hash if prev_entry else None
        sequence_number = (prev_entry.sequence_number + 1) if prev_entry else 1

        # 2. Build the new entry
        entry_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)

        entry_hash = ChainOfCustodyLog.compute_entry_hash(
            entry_id=entry_id,
            entity_type=entity_type,
            entity_id=entity_id,
            sequence_number=sequence_number,
            action=action.value,
            actor_id=actor_id,
            actor_type=actor_type.value,
            entity_hash=entity_hash,
            prev_hash=prev_hash,
            created_at=str(created_at),
        )

        entry = ChainOfCustodyLog(
            id=entry_id,
            entity_type=entity_type,
            entity_id=entity_id,
            sequence_number=sequence_number,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_ip=actor_ip,
            device_fingerprint=device_fingerprint,
            entity_hash=entity_hash,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            metadata_json=metadata,
            created_at=created_at,
        )

        self._db.add(entry)
        await self._db.flush()

        logger.info(
            "Custody event logged: entity=%s:%s seq=%d action=%s hash=%.12s",
            entity_type, entity_id, sequence_number, action.value, entry_hash,
        )
        return entry

    async def verify_chain(self, entity_id: uuid.UUID) -> dict:
        """
        Walk the full custody chain for an entity and verify every hash link.

        Returns:
            A dict with:
              - ``valid``: bool — True if the entire chain is intact.
              - ``total_entries``: int
              - ``broken_links``: list of dicts describing any invalid entries.
        """
        stmt = (
            select(ChainOfCustodyLog)
            .where(ChainOfCustodyLog.entity_id == entity_id)
            .order_by(ChainOfCustodyLog.sequence_number.asc())
        )
        result = await self._db.execute(stmt)
        entries = list(result.scalars().all())

        if not entries:
            return {"valid": True, "total_entries": 0, "broken_links": []}

        broken_links: list[dict] = []
        prev_hash: str | None = None

        for entry in entries:
            # Check 1: prev_hash linkage
            if entry.prev_hash != prev_hash:
                broken_links.append({
                    "entry_id": str(entry.id),
                    "sequence_number": entry.sequence_number,
                    "issue": "prev_hash_mismatch",
                    "expected_prev_hash": prev_hash,
                    "actual_prev_hash": entry.prev_hash,
                })

            # Check 2: entry_hash integrity
            if not entry.verify_integrity():
                broken_links.append({
                    "entry_id": str(entry.id),
                    "sequence_number": entry.sequence_number,
                    "issue": "entry_hash_corrupted",
                    "stored_hash": entry.entry_hash,
                    "recomputed_hash": entry.recompute_hash(),
                })

            prev_hash = entry.entry_hash

        is_valid = len(broken_links) == 0

        if not is_valid:
            logger.warning(
                "Chain of custody INTEGRITY FAILURE for entity %s: %d broken links",
                entity_id, len(broken_links),
            )

        return {
            "valid": is_valid,
            "total_entries": len(entries),
            "broken_links": broken_links,
        }

    async def get_timeline(
        self,
        entity_id: uuid.UUID,
    ) -> list[ChainOfCustodyLog]:
        """
        Return the complete ordered custody history for an entity.

        Args:
            entity_id: UUID of the tracked entity.

        Returns:
            List of ``ChainOfCustodyLog`` entries, oldest first.
        """
        stmt = (
            select(ChainOfCustodyLog)
            .where(ChainOfCustodyLog.entity_id == entity_id)
            .order_by(ChainOfCustodyLog.sequence_number.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ── Helpers ─────────────────────────────────────────────────

    async def _get_latest_entry(
        self, entity_id: uuid.UUID,
    ) -> ChainOfCustodyLog | None:
        """Fetch the most recent custody log entry for an entity."""
        stmt = (
            select(ChainOfCustodyLog)
            .where(ChainOfCustodyLog.entity_id == entity_id)
            .order_by(ChainOfCustodyLog.sequence_number.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def hash_entity(data: dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of an entity's current state.

        The dict is serialised to a canonical JSON string (sorted keys,
        compact separators) before hashing, ensuring deterministic output.

        Args:
            data: Dictionary representing the entity state.

        Returns:
            64-character lowercase hex digest.
        """
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
