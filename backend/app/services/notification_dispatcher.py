"""
Sentinel — Notification Dispatcher Service.

Multi-channel alert delivery via Firebase Cloud Messaging (push),
Twilio SMS, and Twilio Voice.  All dispatches are logged to the
``notification_log`` table.

When ``DRY_RUN=true`` (the default for local dev), messages are
logged but never actually sent to external APIs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import (
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
)

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches alerts via FCM, SMS, and Voice channels."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Public API ──────────────────────────────────────────────

    async def dispatch(
        self,
        responder_id: uuid.UUID,
        channel: NotificationChannel,
        payload: dict[str, Any],
        *,
        escalation_action_id: uuid.UUID | None = None,
        phone_number: str | None = None,
        fcm_token: str | None = None,
    ) -> NotificationLog:
        """
        Send a notification through a specific channel and log the result.

        Args:
            responder_id: Target responder UUID.
            channel: Delivery channel (FCM, SMS, VOICE).
            payload: Alert payload dict (incident details, confidence, etc.).
            escalation_action_id: Optional link to the triggering escalation.
            phone_number: Required for SMS/VOICE channels.
            fcm_token: Required for FCM channel.

        Returns:
            The ``NotificationLog`` entry with delivery status.
        """
        # Create the log entry first (status: QUEUED)
        log_entry = NotificationLog(
            escalation_action_id=escalation_action_id,
            responder_id=responder_id,
            channel=channel,
            status=NotificationStatus.QUEUED,
            payload=payload,
        )
        self._db.add(log_entry)
        await self._db.flush()

        # Dispatch through the appropriate channel
        try:
            if settings.DRY_RUN:
                provider_id = await self._dry_run(channel, responder_id, payload)
            elif channel == NotificationChannel.FCM:
                provider_id = await self._send_fcm(fcm_token, payload)
            elif channel == NotificationChannel.SMS:
                provider_id = await self._send_sms(phone_number, payload)
            elif channel == NotificationChannel.VOICE:
                provider_id = await self._send_voice(phone_number, payload)
            else:
                raise ValueError(f"Unsupported channel: {channel}")

            log_entry.status = NotificationStatus.SENT
            log_entry.provider_message_id = provider_id
            log_entry.sent_at = datetime.now(timezone.utc)

        except Exception as exc:
            log_entry.status = NotificationStatus.FAILED
            log_entry.error_message = str(exc)[:1024]
            logger.error(
                "Notification FAILED: channel=%s responder=%s error=%s",
                channel.value, responder_id, exc,
            )

        await self._db.flush()
        return log_entry

    async def dispatch_multi_channel(
        self,
        responder_id: uuid.UUID,
        channels: list[str],
        payload: dict[str, Any],
        *,
        escalation_action_id: uuid.UUID | None = None,
        phone_number: str | None = None,
        fcm_token: str | None = None,
    ) -> list[NotificationLog]:
        """
        Dispatch the same alert through multiple channels in order.

        Args:
            responder_id: Target responder UUID.
            channels: Ordered list of channel names, e.g. ``["FCM", "SMS"]``.
            payload: Alert payload dict.
            escalation_action_id: Optional link to the triggering escalation.
            phone_number: Responder's phone number.
            fcm_token: Responder's FCM registration token.

        Returns:
            List of ``NotificationLog`` entries, one per channel.
        """
        results: list[NotificationLog] = []
        for ch_name in channels:
            try:
                channel = NotificationChannel(ch_name)
            except ValueError:
                logger.warning("Skipping unknown channel: %s", ch_name)
                continue

            log_entry = await self.dispatch(
                responder_id=responder_id,
                channel=channel,
                payload=payload,
                escalation_action_id=escalation_action_id,
                phone_number=phone_number,
                fcm_token=fcm_token,
            )
            results.append(log_entry)

        return results

    # ── Channel Implementations ─────────────────────────────────

    async def _dry_run(
        self,
        channel: NotificationChannel,
        responder_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> str:
        """Log the notification without sending (DRY_RUN mode)."""
        logger.info(
            "[DRY_RUN] Would send %s to responder %s | payload=%s",
            channel.value, responder_id, payload.get("title", "N/A"),
        )
        return f"dry_run_{channel.value}_{uuid.uuid4().hex[:12]}"

    async def _send_fcm(
        self,
        fcm_token: str | None,
        payload: dict[str, Any],
    ) -> str:
        """Send a push notification via Firebase Cloud Messaging."""
        if not fcm_token:
            raise ValueError("FCM token is required for push notifications")

        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title=payload.get("title", "Sentinel Alert"),
                body=payload.get("body", "An incident requires your attention."),
            ),
            data={k: str(v) for k, v in payload.items()},
            token=fcm_token,
        )
        response = messaging.send(message)
        logger.info("FCM sent: message_id=%s", response)
        return response

    async def _send_sms(
        self,
        phone_number: str | None,
        payload: dict[str, Any],
    ) -> str:
        """Send an SMS alert via Twilio."""
        if not phone_number:
            raise ValueError("Phone number is required for SMS")

        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        body = (
            f"🚨 SENTINEL ALERT: {payload.get('title', 'Incident')}\n"
            f"Severity: {payload.get('severity', 'N/A')}\n"
            f"Confidence: {payload.get('confidence', 'N/A')}\n"
            f"Location: {payload.get('zone', 'Unknown')}\n"
            f"Acknowledge at: {payload.get('ack_url', 'N/A')}"
        )

        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone_number,
        )
        logger.info("SMS sent: sid=%s to=%s", message.sid, phone_number)
        return message.sid

    async def _send_voice(
        self,
        phone_number: str | None,
        payload: dict[str, Any],
    ) -> str:
        """Initiate a voice call via Twilio (for T3+ escalations)."""
        if not phone_number:
            raise ValueError("Phone number is required for voice calls")

        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        twiml = (
            '<Response>'
            '<Say voice="alice">'
            f"Sentinel emergency alert. {payload.get('title', 'Incident detected')}. "
            f"Severity: {payload.get('severity', 'unknown')}. "
            'Press 1 to acknowledge.'
            '</Say>'
            '<Gather numDigits="1" action="/api/v1/twilio/gather" method="POST">'
            '<Say voice="alice">Press 1 to acknowledge this alert.</Say>'
            '</Gather>'
            '</Response>'
        )

        call = client.calls.create(
            twiml=twiml,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone_number,
        )
        logger.info("Voice call initiated: sid=%s to=%s", call.sid, phone_number)
        return call.sid
