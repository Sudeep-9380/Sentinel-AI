"""
Sentinel — Multi-Tier Escalation Engine.

Central orchestrator for the escalation workflow:

  1. An AI detection triggers ``trigger_escalation(incident_id)``.
  2. The engine matches the incident's threat_type + severity against
     ``escalation_rules`` to determine which responder tier to notify.
  3. Responders in that tier are ranked by GPS proximity (Haversine)
     to the incident location.
  4. Notifications are dispatched via FCM/SMS/Voice.
  5. A 60-second Celery countdown task is scheduled.
  6. If no acknowledgement arrives within the SLA, the engine
     auto-escalates to the next tier (``check_and_escalate``).
  7. When a responder acknowledges, all pending timers for that
     incident are cancelled (``acknowledge``).

All state transitions are recorded in the audit log and, for
evidence-related actions, in the chain of custody.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.escalation import (
    EscalationAction,
    EscalationRule,
    EscalationStatus,
    IncidentAcknowledgement,
)
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.responder import Responder, ResponderTier
from app.services.audit_service import AuditService
from app.services.chain_of_custody import ChainOfCustodyService
from app.services.notification_dispatcher import NotificationDispatcher
from app.models.audit import AuditActorType, CustodyAction, CustodyActorType

logger = logging.getLogger(__name__)

# Severity ordering for comparison (higher value = more severe)
SEVERITY_RANK: dict[str, int] = {
    Severity.LOW.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.HIGH.value: 3,
    Severity.CRITICAL.value: 4,
}

# Earth radius in kilometres for Haversine
_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two GPS points.

    Uses the Haversine formula with the WGS-84 mean Earth radius.

    Args:
        lat1, lon1: Latitude and longitude of point A (degrees).
        lat2, lon2: Latitude and longitude of point B (degrees).

    Returns:
        Distance in kilometres.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class EscalationEngine:
    """
    Orchestrates the multi-tier escalation lifecycle.

    Instantiate with an ``AsyncSession`` — all three dependent services
    (audit, custody, notifications) share the same session/transaction.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._audit = AuditService(db)
        self._custody = ChainOfCustodyService(db)
        self._notifier = NotificationDispatcher(db)

    # ── 1. Trigger ──────────────────────────────────────────────

    async def trigger_escalation(
        self,
        incident_id: uuid.UUID,
    ) -> EscalationAction | None:
        """
        Initiate the escalation workflow for an incident.

        Steps:
          1. Load the incident with its threat type.
          2. Find the matching escalation rule (lowest priority_order).
          3. Query on-duty responders in the target tier, ranked by
             Haversine distance to the incident GPS.
          4. Create an ``EscalationAction`` row.
          5. Dispatch notifications to the nearest responders.
          6. Schedule a 60-second Celery countdown for auto-escalation.
          7. Update incident status to ``ESCALATED``.

        Returns:
            The created ``EscalationAction``, or None if no matching rule.
        """
        # ── Load incident ───────────────────────────────────────
        incident = await self._db.get(Incident, incident_id)
        if not incident:
            logger.error("Incident %s not found", incident_id)
            return None

        logger.info(
            "Triggering escalation for incident %s (threat=%s, severity=%s)",
            incident.incident_number, incident.threat_type_id, incident.severity.value,
        )

        # ── Find matching rule ──────────────────────────────────
        rule = await self._find_matching_rule(
            threat_type_id=incident.threat_type_id,
            severity=incident.severity,
            zone_id=incident.zone_id,
        )
        if not rule:
            logger.warning(
                "No escalation rule matches incident %s — no escalation triggered",
                incident.incident_number,
            )
            return None

        # ── Find nearest responders ─────────────────────────────
        responders = await self._find_nearest_responders(
            tier_id=rule.responder_tier_id,
            incident_lat=incident.gps_latitude,
            incident_lon=incident.gps_longitude,
            limit=5,
        )

        if not responders:
            logger.warning(
                "No on-duty responders in tier %s — attempting next tier",
                rule.responder_tier_id,
            )
            # Attempt to find a rule for the next tier up
            return await self._escalate_to_next_tier(incident, rule)

        # ── Create escalation action ────────────────────────────
        action = EscalationAction(
            incident_id=incident.id,
            escalation_rule_id=rule.id,
            responder_tier_id=rule.responder_tier_id,
            status=EscalationStatus.DISPATCHED,
            dispatched_at=datetime.now(timezone.utc),
            attempt_number=1,
        )
        self._db.add(action)
        await self._db.flush()  # Get the action.id

        # ── Dispatch notifications ──────────────────────────────
        channels = rule.notification_channels or ["FCM", "SMS"]
        alert_payload = self._build_alert_payload(incident, rule)

        for responder in responders:
            await self._notifier.dispatch_multi_channel(
                responder_id=responder.id,
                channels=channels,
                payload=alert_payload,
                escalation_action_id=action.id,
                phone_number=responder.phone_number,
                fcm_token=responder.fcm_token,
            )

        # ── Schedule 60-second timeout ──────────────────────────
        celery_task_id = self._schedule_timeout_check(action.id, rule.sla_seconds)
        action.celery_task_id = celery_task_id

        # ── Update incident status ──────────────────────────────
        incident.status = IncidentStatus.ESCALATED
        await self._db.flush()

        # ── Audit ───────────────────────────────────────────────
        await self._audit.log(
            action="escalation.triggered",
            entity_type="incident",
            entity_id=incident.id,
            after_state={
                "escalation_action_id": str(action.id),
                "tier": str(rule.responder_tier_id),
                "responders_notified": len(responders),
                "channels": channels,
                "sla_seconds": rule.sla_seconds,
            },
        )

        logger.info(
            "Escalation dispatched: action=%s tier=%s responders=%d sla=%ds",
            action.id, rule.responder_tier_id, len(responders), rule.sla_seconds,
        )
        return action

    # ── 2. Timeout Check ────────────────────────────────────────

    async def check_and_escalate(
        self,
        escalation_action_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Called by Celery after the SLA timeout.

        If the action is still DISPATCHED (not acknowledged), mark it
        TIMED_OUT and trigger escalation to the next tier.

        Returns:
            Dict with ``"outcome"`` key: ``"acknowledged"``, ``"escalated"``,
            or ``"no_next_tier"``.
        """
        action = await self._db.get(EscalationAction, escalation_action_id)
        if not action:
            logger.error("EscalationAction %s not found", escalation_action_id)
            return {"outcome": "error", "detail": "action_not_found"}

        # Already acknowledged — no-op
        if action.status == EscalationStatus.ACKNOWLEDGED:
            logger.info(
                "Action %s already acknowledged — skipping escalation",
                escalation_action_id,
            )
            return {"outcome": "acknowledged"}

        # Already escalated or cancelled — no-op
        if action.status in (EscalationStatus.ESCALATED, EscalationStatus.CANCELLED):
            return {"outcome": action.status.value.lower()}

        # ── Mark as timed out ───────────────────────────────────
        action.status = EscalationStatus.TIMED_OUT
        action.escalated_at = datetime.now(timezone.utc)
        await self._db.flush()

        # ── Load context ────────────────────────────────────────
        incident = await self._db.get(Incident, action.incident_id)
        rule = await self._db.get(EscalationRule, action.escalation_rule_id)

        if not incident or not rule:
            return {"outcome": "error", "detail": "missing_context"}

        # ── Audit the timeout ───────────────────────────────────
        await self._audit.log(
            action="escalation.timed_out",
            entity_type="escalation_action",
            entity_id=action.id,
            before_state={"status": "DISPATCHED"},
            after_state={"status": "TIMED_OUT", "sla_seconds": rule.sla_seconds},
        )

        # ── Escalate to next tier ───────────────────────────────
        next_action = await self._escalate_to_next_tier(incident, rule)

        if next_action:
            action.status = EscalationStatus.ESCALATED
            await self._db.flush()

            logger.warning(
                "Escalation TIMEOUT: action=%s → escalated to tier %s",
                escalation_action_id, next_action.responder_tier_id,
            )
            return {
                "outcome": "escalated",
                "new_action_id": str(next_action.id),
                "new_tier_id": str(next_action.responder_tier_id),
            }
        else:
            logger.critical(
                "Escalation TIMEOUT: action=%s — NO HIGHER TIER AVAILABLE",
                escalation_action_id,
            )
            return {"outcome": "no_next_tier"}

    # ── 3. Acknowledge ──────────────────────────────────────────

    async def acknowledge(
        self,
        escalation_action_id: uuid.UUID,
        responder_id: uuid.UUID,
        *,
        gps_latitude: float | None = None,
        gps_longitude: float | None = None,
        device_info: dict | None = None,
        notes: str | None = None,
    ) -> IncidentAcknowledgement | None:
        """
        Record a responder's acknowledgement of an escalation.

        Steps:
          1. Validate the action exists and is in an ack-able state.
          2. Mark the ``EscalationAction`` as ACKNOWLEDGED.
          3. Create an ``IncidentAcknowledgement`` record.
          4. Update the incident status to ACKNOWLEDGED.
          5. Cancel any pending Celery timeout tasks for this incident.
          6. Log to audit trail.

        Returns:
            The ``IncidentAcknowledgement`` row, or None on failure.
        """
        action = await self._db.get(EscalationAction, escalation_action_id)
        if not action:
            logger.error("EscalationAction %s not found", escalation_action_id)
            return None

        if action.status == EscalationStatus.ACKNOWLEDGED:
            logger.info("Action %s already acknowledged", escalation_action_id)
            return None

        now = datetime.now(timezone.utc)

        # ── Mark action as acknowledged ─────────────────────────
        action.status = EscalationStatus.ACKNOWLEDGED
        action.acknowledged_at = now
        action.acknowledged_by_id = responder_id

        # ── Create acknowledgement record ───────────────────────
        ack = IncidentAcknowledgement(
            incident_id=action.incident_id,
            escalation_action_id=action.id,
            responder_id=responder_id,
            acknowledged_at=now,
            gps_latitude=gps_latitude,
            gps_longitude=gps_longitude,
            device_info=device_info,
            notes=notes,
        )
        self._db.add(ack)

        # ── Update incident status ──────────────────────────────
        incident = await self._db.get(Incident, action.incident_id)
        if incident:
            incident.status = IncidentStatus.ACKNOWLEDGED
            await self._db.flush()

        # ── Cancel all pending escalation timers for this incident
        await self._cancel_pending_actions(action.incident_id, exclude_id=action.id)

        # ── Audit ───────────────────────────────────────────────
        await self._audit.log(
            action="escalation.acknowledged",
            entity_type="escalation_action",
            entity_id=action.id,
            actor_id=responder_id,
            actor_type=AuditActorType.RESPONDER,
            after_state={
                "responder_id": str(responder_id),
                "gps": [gps_latitude, gps_longitude],
                "acknowledged_at": str(now),
            },
        )

        # ── Chain of custody (if evidence exists) ───────────────
        evidence_stmt = select(Incident).where(Incident.id == action.incident_id)
        result = await self._db.execute(evidence_stmt)
        inc = result.scalar_one_or_none()
        if inc:
            await self._custody.log_event(
                entity_type="incident",
                entity_id=inc.id,
                action=CustodyAction.ACCESSED,
                actor_id=responder_id,
                actor_type=CustodyActorType.RESPONDER,
                entity_hash=self._custody.hash_entity({
                    "incident_id": str(inc.id),
                    "status": inc.status.value,
                }),
            )

        await self._db.flush()

        logger.info(
            "Escalation ACKNOWLEDGED: action=%s by responder=%s",
            escalation_action_id, responder_id,
        )
        return ack

    # ── Internal Helpers ────────────────────────────────────────

    async def _find_matching_rule(
        self,
        threat_type_id: uuid.UUID,
        severity: Severity,
        zone_id: uuid.UUID,
    ) -> EscalationRule | None:
        """
        Find the best-matching escalation rule for the given parameters.

        Matches on threat_type, checks that the incident severity is
        >= the rule's min_severity, and optionally filters by zone.
        Returns the rule with the lowest ``priority_order``.
        """
        incident_rank = SEVERITY_RANK.get(severity.value, 0)

        stmt = (
            select(EscalationRule)
            .where(
                and_(
                    EscalationRule.threat_type_id == threat_type_id,
                    EscalationRule.is_active == True,
                    or_(
                        EscalationRule.zone_id == zone_id,
                        EscalationRule.zone_id.is_(None),
                    ),
                )
            )
            .order_by(EscalationRule.priority_order.asc())
        )
        result = await self._db.execute(stmt)
        rules = list(result.scalars().all())

        # Filter by severity rank in Python (since min_severity is an enum)
        for rule in rules:
            rule_rank = SEVERITY_RANK.get(rule.min_severity.value, 0)
            if incident_rank >= rule_rank:
                return rule

        return None

    async def _find_nearest_responders(
        self,
        tier_id: uuid.UUID,
        incident_lat: float,
        incident_lon: float,
        limit: int = 5,
    ) -> list[Responder]:
        """
        Find on-duty responders in a tier, ranked by GPS distance.

        Only includes responders who have GPS coordinates and are both
        active and on duty.
        """
        stmt = (
            select(Responder)
            .where(
                and_(
                    Responder.tier_id == tier_id,
                    Responder.is_on_duty == True,
                    Responder.is_active == True,
                    Responder.deleted_at.is_(None),
                    Responder.latitude.isnot(None),
                    Responder.longitude.isnot(None),
                )
            )
        )
        result = await self._db.execute(stmt)
        responders = list(result.scalars().all())

        # Sort by Haversine distance
        responders.sort(
            key=lambda r: haversine_km(
                incident_lat, incident_lon,
                r.latitude, r.longitude,  # type: ignore[arg-type]
            )
        )

        return responders[:limit]

    async def _escalate_to_next_tier(
        self,
        incident: Incident,
        current_rule: EscalationRule,
    ) -> EscalationAction | None:
        """
        Find the next-higher tier's rule and trigger escalation.

        Looks for a rule with a higher ``priority_order`` for the same
        threat type.
        """
        stmt = (
            select(EscalationRule)
            .where(
                and_(
                    EscalationRule.threat_type_id == incident.threat_type_id,
                    EscalationRule.is_active == True,
                    EscalationRule.priority_order > current_rule.priority_order,
                )
            )
            .order_by(EscalationRule.priority_order.asc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        next_rule = result.scalar_one_or_none()

        if not next_rule:
            return None

        # Recursively trigger with the next rule's tier
        responders = await self._find_nearest_responders(
            tier_id=next_rule.responder_tier_id,
            incident_lat=incident.gps_latitude,
            incident_lon=incident.gps_longitude,
        )

        action = EscalationAction(
            incident_id=incident.id,
            escalation_rule_id=next_rule.id,
            responder_tier_id=next_rule.responder_tier_id,
            status=EscalationStatus.DISPATCHED,
            dispatched_at=datetime.now(timezone.utc),
            attempt_number=1,
        )
        self._db.add(action)
        await self._db.flush()

        # Dispatch to whatever responders are available
        if responders:
            channels = next_rule.notification_channels or ["FCM", "SMS", "VOICE"]
            alert_payload = self._build_alert_payload(incident, next_rule)

            for responder in responders:
                await self._notifier.dispatch_multi_channel(
                    responder_id=responder.id,
                    channels=channels,
                    payload=alert_payload,
                    escalation_action_id=action.id,
                    phone_number=responder.phone_number,
                    fcm_token=responder.fcm_token,
                )

        # Schedule the next timeout
        celery_task_id = self._schedule_timeout_check(action.id, next_rule.sla_seconds)
        action.celery_task_id = celery_task_id
        await self._db.flush()

        await self._audit.log(
            action="escalation.tier_elevated",
            entity_type="incident",
            entity_id=incident.id,
            after_state={
                "new_action_id": str(action.id),
                "new_tier": str(next_rule.responder_tier_id),
                "previous_rule": str(next_rule.id),
            },
        )

        return action

    async def _cancel_pending_actions(
        self,
        incident_id: uuid.UUID,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> int:
        """
        Cancel all PENDING/DISPATCHED escalation actions for an incident.

        Also attempts to revoke the associated Celery tasks.

        Returns:
            Number of actions cancelled.
        """
        stmt = select(EscalationAction).where(
            and_(
                EscalationAction.incident_id == incident_id,
                EscalationAction.status.in_([
                    EscalationStatus.PENDING,
                    EscalationStatus.DISPATCHED,
                ]),
            )
        )
        if exclude_id:
            stmt = stmt.where(EscalationAction.id != exclude_id)

        result = await self._db.execute(stmt)
        actions = list(result.scalars().all())

        cancelled = 0
        for act in actions:
            act.status = EscalationStatus.CANCELLED

            # Revoke the Celery task if it exists
            if act.celery_task_id:
                try:
                    from app.workers.celery_app import celery_app
                    celery_app.control.revoke(act.celery_task_id, terminate=False)
                except Exception as exc:
                    logger.warning(
                        "Failed to revoke Celery task %s: %s",
                        act.celery_task_id, exc,
                    )
            cancelled += 1

        if cancelled:
            await self._db.flush()
            logger.info(
                "Cancelled %d pending escalation actions for incident %s",
                cancelled, incident_id,
            )

        return cancelled

    def _build_alert_payload(
        self,
        incident: Incident,
        rule: EscalationRule,
    ) -> dict[str, Any]:
        """Build the notification payload dict for an escalation alert."""
        return {
            "title": f"🚨 {incident.severity.value} — Incident {incident.incident_number}",
            "body": incident.summary or "An incident requires your immediate attention.",
            "incident_id": str(incident.id),
            "incident_number": incident.incident_number,
            "severity": incident.severity.value,
            "threat_type_id": str(incident.threat_type_id),
            "confidence": str(incident.ai_confidence),
            "gps_latitude": str(incident.gps_latitude),
            "gps_longitude": str(incident.gps_longitude),
            "zone_id": str(incident.zone_id),
            "ack_url": f"/api/v1/incidents/{incident.id}/acknowledge",
            "sla_seconds": str(rule.sla_seconds),
        }

    @staticmethod
    def _schedule_timeout_check(
        action_id: uuid.UUID,
        sla_seconds: int,
    ) -> str | None:
        """
        Schedule a Celery task to check for timeout after ``sla_seconds``.

        Returns:
            The Celery AsyncResult task ID, or None on failure.
        """
        try:
            from app.workers.escalation_tasks import check_escalation_timeout
            result = check_escalation_timeout.apply_async(
                args=[str(action_id)],
                countdown=sla_seconds,
            )
            logger.info(
                "Scheduled timeout check: action=%s in %ds (task=%s)",
                action_id, sla_seconds, result.id,
            )
            return result.id
        except Exception as exc:
            logger.error(
                "Failed to schedule Celery timeout task for action %s: %s",
                action_id, exc,
            )
            return None
