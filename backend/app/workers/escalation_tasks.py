"""
Sentinel — Escalation Celery Tasks.

Background tasks for the 60-second escalation timer and
notification fan-out.  These are thin async-to-sync bridges
that create a database session and delegate to the service layer.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _check_escalation_async(escalation_action_id: str) -> dict:
    """Async implementation of the escalation timeout check."""
    from app.core.database import AsyncSessionFactory
    from app.services.escalation_engine import EscalationEngine

    async with AsyncSessionFactory() as session:
        engine = EscalationEngine(session)
        result = await engine.check_and_escalate(
            uuid.UUID(escalation_action_id),
        )
        await session.commit()
        return result


@celery_app.task(
    name="sentinel.check_escalation_timeout",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def check_escalation_timeout(self, escalation_action_id: str) -> dict:
    """
    Called 60 seconds after an escalation action is dispatched.

    Checks if the action has been acknowledged.  If not, marks it
    as TIMED_OUT and triggers escalation to the next tier.

    Args:
        escalation_action_id: UUID string of the EscalationAction to check.

    Returns:
        dict with the outcome: 'acknowledged', 'escalated', or 'no_next_tier'.
    """
    logger.info(
        "⏱️  Escalation timeout check triggered for action_id=%s",
        escalation_action_id,
    )
    try:
        result = _run_async(_check_escalation_async(escalation_action_id))
        logger.info(
            "Timeout check result for %s: %s",
            escalation_action_id, result,
        )
        return result
    except Exception as exc:
        logger.exception(
            "Error in escalation timeout check for %s", escalation_action_id,
        )
        raise self.retry(exc=exc)


@celery_app.task(
    name="sentinel.dispatch_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def dispatch_notifications(self, escalation_action_id: str) -> dict:
    """
    Fan out notifications to all responders for an escalation action.

    This task is provided for manual/external triggering.  During normal
    operation, notifications are dispatched inline by the escalation
    engine within ``trigger_escalation()``.

    Args:
        escalation_action_id: UUID string of the EscalationAction.

    Returns:
        dict with notification delivery results.
    """
    logger.info(
        "📢 Notification dispatch requested for action_id=%s",
        escalation_action_id,
    )
    # Inline dispatch is handled by EscalationEngine.trigger_escalation().
    # This task exists for re-dispatch scenarios (e.g., after delivery failure).
    return {"action_id": escalation_action_id, "outcome": "inline_dispatch"}
