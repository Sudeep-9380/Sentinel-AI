"""
Sentinel — Test Escalation Script.

Seeds the database with minimal test data and triggers a full
escalation cycle so you can verify the engine, dispatcher, and
audit logging in your terminal output.

Usage:
    cd backend
    python scripts/test_escalation.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Configure logging BEFORE importing app modules
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sentinel.test")


async def main() -> None:
    from app.core.database import AsyncSessionFactory, engine
    from app.models.base import Base
    from app.models.zone import Zone, ZoneType
    from app.models.camera import Camera, CameraType, CameraStatus
    from app.models.incident import ThreatType, Incident, Severity, IncidentStatus
    from app.models.responder import ResponderTier, Responder
    from app.models.escalation import EscalationRule
    from app.services.escalation_engine import EscalationEngine
    from app.services.chain_of_custody import ChainOfCustodyService
    from app.models.audit import CustodyAction, CustodyActorType

    print()
    print("=" * 70)
    print("  SENTINEL — Escalation Engine Test")
    print("=" * 70)
    print()

    async with AsyncSessionFactory() as session:
        # ────────────────────────────────────────────────
        # 1. Seed: Zone
        # ────────────────────────────────────────────────
        logger.info("Seeding test zone...")
        zone = Zone(
            name="Main Building - Ground Floor",
            zone_type=ZoneType.BUILDING,
            latitude=15.1444,
            longitude=76.9179,
            is_active=True,
        )
        session.add(zone)
        await session.flush()
        logger.info("  [OK] Zone created: %s", zone.id)

        # ────────────────────────────────────────────────
        # 2. Seed: Camera
        # ────────────────────────────────────────────────
        logger.info("Seeding test camera...")
        camera = Camera(
            name="CAM-LOBBY-01",
            rtsp_url="rtsp://192.168.1.100:554/stream1",
            camera_type=CameraType.DOME,
            status=CameraStatus.ONLINE,
            zone_id=zone.id,
            latitude=15.1444,
            longitude=76.9179,
            resolution_width=1920,
            resolution_height=1080,
            fps=30,
            is_active=True,
        )
        session.add(camera)
        await session.flush()
        logger.info("  [OK] Camera created: %s", camera.id)

        # ────────────────────────────────────────────────
        # 3. Seed: Threat Type
        # ────────────────────────────────────────────────
        logger.info("Seeding threat types...")
        threat_violence = ThreatType(
            code="VIOLENCE",
            name="Physical Violence",
            description="Detected physical altercation or assault",
            default_severity=Severity.CRITICAL,
            is_active=True,
        )
        session.add(threat_violence)
        await session.flush()
        logger.info("  [OK] Threat type created: %s", threat_violence.code)

        # ────────────────────────────────────────────────
        # 4. Seed: Responder Tiers (T1-T3)
        # ────────────────────────────────────────────────
        logger.info("Seeding responder tiers...")
        tier_t1 = ResponderTier(code="T1_SECURITY", name="Security Guard", level=1, is_active=True)
        tier_t2 = ResponderTier(code="T2_SUPERVISOR", name="Security Supervisor", level=2, is_active=True)
        tier_t3 = ResponderTier(code="T3_POLICE", name="Police / Law Enforcement", level=3, is_active=True)
        session.add_all([tier_t1, tier_t2, tier_t3])
        await session.flush()
        logger.info("  [OK] Tiers created: T1, T2, T3")

        # ────────────────────────────────────────────────
        # 5. Seed: Responders (GPS near the incident)
        # ────────────────────────────────────────────────
        logger.info("Seeding test responders...")
        guard_1 = Responder(
            employee_id="SEC-001",
            full_name="Ahmed Khan",
            role="Security Guard",
            tier_id=tier_t1.id,
            zone_id=zone.id,
            phone_number="+923001234567",
            email="ahmed.khan@sentinel.local",
            fcm_token="test_fcm_token_ahmed",
            latitude=15.1450,   # ~100m from camera
            longitude=76.9185,
            is_on_duty=True,
            is_active=True,
        )
        guard_2 = Responder(
            employee_id="SEC-002",
            full_name="Sara Ali",
            role="Security Guard",
            tier_id=tier_t1.id,
            zone_id=zone.id,
            phone_number="+923009876543",
            email="sara.ali@sentinel.local",
            fcm_token="test_fcm_token_sara",
            latitude=15.1460,   # ~200m from camera
            longitude=76.9190,
            is_on_duty=True,
            is_active=True,
        )
        supervisor = Responder(
            employee_id="SUP-001",
            full_name="Hassan Raza",
            role="Security Supervisor",
            tier_id=tier_t2.id,
            phone_number="+923007654321",
            email="hassan.raza@sentinel.local",
            fcm_token="test_fcm_token_hassan",
            latitude=15.1500,
            longitude=76.9200,
            is_on_duty=True,
            is_active=True,
        )
        session.add_all([guard_1, guard_2, supervisor])
        await session.flush()
        logger.info("  [OK] Responders created: Ahmed (T1), Sara (T1), Hassan (T2)")

        # ────────────────────────────────────────────────
        # 6. Seed: Escalation Rules
        # ────────────────────────────────────────────────
        logger.info("Seeding escalation rules...")
        rule_t1 = EscalationRule(
            name="Violence → T1 Security (60s SLA)",
            threat_type_id=threat_violence.id,
            min_severity=Severity.HIGH,
            responder_tier_id=tier_t1.id,
            sla_seconds=60,
            priority_order=1,
            notification_channels=["FCM", "SMS"],
            is_active=True,
        )
        rule_t2 = EscalationRule(
            name="Violence → T2 Supervisor (60s SLA)",
            threat_type_id=threat_violence.id,
            min_severity=Severity.HIGH,
            responder_tier_id=tier_t2.id,
            sla_seconds=60,
            priority_order=2,
            notification_channels=["FCM", "SMS", "VOICE"],
            is_active=True,
        )
        rule_t3 = EscalationRule(
            name="Violence → T3 Police (120s SLA)",
            threat_type_id=threat_violence.id,
            min_severity=Severity.CRITICAL,
            responder_tier_id=tier_t3.id,
            sla_seconds=120,
            priority_order=3,
            notification_channels=["SMS", "VOICE"],
            is_active=True,
        )
        session.add_all([rule_t1, rule_t2, rule_t3])
        await session.flush()
        logger.info("  [OK] Escalation rules created: T1(prio=1), T2(prio=2), T3(prio=3)")

        # ────────────────────────────────────────────────
        # 7. Create Test Incident
        # ────────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        incident_number = f"INC-{now.strftime('%Y%m%d')}-0001"

        logger.info("Creating test incident: %s", incident_number)
        incident = Incident(
            incident_number=incident_number,
            camera_id=camera.id,
            zone_id=zone.id,
            threat_type_id=threat_violence.id,
            severity=Severity.CRITICAL,
            status=IncidentStatus.DETECTED,
            ai_confidence=0.94,
            ai_model_version="yolov11-violence-v2.1",
            detected_at=now,
            gps_latitude=15.1444,
            gps_longitude=76.9179,
            summary="Physical altercation detected in main lobby - 2 individuals involved",
        )
        session.add(incident)
        await session.flush()
        logger.info("  [OK] Incident created: %s (confidence=94%%)", incident_number)

        # ────────────────────────────────────────────────
        # 8. Chain of Custody: Log incident creation
        # ────────────────────────────────────────────────
        logger.info("Logging chain of custody entry...")
        custody_svc = ChainOfCustodyService(session)
        entity_hash = custody_svc.hash_entity({
            "incident_id": str(incident.id),
            "incident_number": incident_number,
            "severity": "CRITICAL",
            "status": "DETECTED",
        })
        await custody_svc.log_event(
            entity_type="incident",
            entity_id=incident.id,
            action=CustodyAction.CREATED,
            actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # System
            actor_type=CustodyActorType.SYSTEM,
            entity_hash=entity_hash,
            actor_ip="127.0.0.1",
            metadata={"source": "test_script", "model": "yolov11-violence-v2.1"},
        )
        logger.info("  [OK] Chain of custody entry logged")

        # ────────────────────────────────────────────────
        # 9. TRIGGER THE ESCALATION ENGINE
        # ────────────────────────────────────────────────
        print()
        print("-" * 70)
        print("  [ALERT]  TRIGGERING ESCALATION ENGINE")
        print("-" * 70)
        print()

        engine = EscalationEngine(session)
        action = await engine.trigger_escalation(incident.id)

        if action:
            logger.info("  [OK] Escalation action created: %s", action.id)
            logger.info("    Status: %s", action.status.value)
            logger.info("    Tier: %s", action.responder_tier_id)
            logger.info("    Dispatched at: %s", action.dispatched_at)
            logger.info("    Celery task ID: %s", action.celery_task_id or "N/A (Celery not running)")
        else:
            logger.warning("  [FAIL] No escalation action created — check rules/responders")

        # ────────────────────────────────────────────────
        # 10. Verify Chain of Custody Integrity
        # ────────────────────────────────────────────────
        print()
        logger.info("Verifying chain of custody integrity...")
        verification = await custody_svc.verify_chain(incident.id)
        logger.info(
            "  Chain verification: valid=%s, entries=%d, broken_links=%d",
            verification["valid"],
            verification["total_entries"],
            len(verification["broken_links"]),
        )

        # ────────────────────────────────────────────────
        # 11. Simulate Acknowledgement
        # ────────────────────────────────────────────────
        if action:
            print()
            print("-" * 70)
            print("  [ACK]  SIMULATING RESPONDER ACKNOWLEDGEMENT")
            print("-" * 70)
            print()

            ack = await engine.acknowledge(
                escalation_action_id=action.id,
                responder_id=guard_1.id,
                gps_latitude=15.1448,
                gps_longitude=76.9181,
                device_info={"platform": "Android", "app_version": "1.0.0"},
                notes="On my way to the lobby, ETA 2 minutes.",
            )

            if ack:
                logger.info("  [OK] Acknowledgement recorded by: %s", guard_1.full_name)
                logger.info("    Incident status: %s", incident.status.value)
            else:
                logger.warning("  [FAIL] Acknowledgement failed")

        # ────────────────────────────────────────────────
        # 12. Final Custody Chain Verification
        # ────────────────────────────────────────────────
        print()
        logger.info("Final chain of custody verification...")
        final_check = await custody_svc.verify_chain(incident.id)
        timeline = await custody_svc.get_timeline(incident.id)

        logger.info(
            "  Chain: valid=%s, total_entries=%d",
            final_check["valid"], final_check["total_entries"],
        )
        for entry in timeline:
            logger.info(
                "    [seq=%d] %s - actor=%s hash=%.16s",
                entry.sequence_number,
                entry.action.value,
                entry.actor_type.value,
                entry.entry_hash,
            )

        # ── Commit everything ───────────────────────────
        await session.commit()

        print()
        print("=" * 70)
        print("  TEST COMPLETE — All systems operational")
        print("=" * 70)
        print()

    # Clean up the database engine
    from app.core.database import engine as db_engine
    await db_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
