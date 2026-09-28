"""
Sentinel — AI Detector Simulator.

Uses OpenCV to open the webcam and simulate AI detections.
Press 'f' to trigger a FIRE incident.
Press 'a' to trigger an ACCIDENT incident.
Press 'q' to quit.
"""

import asyncio
import cv2
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
import urllib.request
from pathlib import Path

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionFactory
from app.models.camera import Camera
from app.models.incident import ThreatType, Severity
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sentinel.ai")

API_URL = "http://localhost:8000/api/v1/incidents"

async def setup_db_context():
    """Fetch or create necessary database references."""
    async with AsyncSessionFactory() as session:
        # Get first available camera
        result = await session.execute(select(Camera).limit(1))
        camera = result.scalars().first()
        if not camera:
            logger.error("No camera found in database. Run test_escalation.py first to seed data.")
            sys.exit(1)

        # Ensure FIRE and ACCIDENT threat types exist
        threat_codes = ["FIRE", "ACCIDENT"]
        threats = {}
        for code in threat_codes:
            result = await session.execute(select(ThreatType).where(ThreatType.code == code))
            threat = result.scalars().first()
            if not threat:
                threat = ThreatType(
                    code=code,
                    name=code.capitalize(),
                    description=f"Simulated {code} detection",
                    default_severity=Severity.CRITICAL if code == "FIRE" else Severity.HIGH,
                    is_active=True
                )
                session.add(threat)
                await session.flush()
            threats[code] = threat
        
        await session.commit()
        return camera, threats

def trigger_incident(camera, threat, severity):
    """Send a POST request to the Sentinel backend."""
    now = datetime.now(timezone.utc)
    incident_number = f"INC-{now.strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}"
    
    payload = {
        "incident_number": incident_number,
        "camera_id": str(camera.id),
        "zone_id": str(camera.zone_id),
        "threat_type_id": str(threat.id),
        "severity": severity,
        "ai_confidence": 0.95,
        "ai_model_version": "sentinel-cv-v1",
        "detected_at": now.isoformat(),
        "gps_latitude": 15.14 + (hash(incident_number) % 100) / 10000.0,
        "gps_longitude": 76.91 + (hash(incident_number) % 100) / 10000.0,
        "summary": f"Simulated {threat.code} detected by AI detector script."
    }

    req = urllib.request.Request(
        API_URL, 
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                logger.info(f"✅ Successfully triggered {threat.code} incident: {incident_number}")
            else:
                logger.error(f"❌ Failed to trigger incident. Status: {response.status}")
    except Exception as e:
        logger.error(f"❌ Network error while triggering incident: {e}")


def run_detector(camera, threats):
    """Open webcam and listen for triggers."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Could not open webcam.")
        sys.exit(1)

    logger.info("SENTINEL AI DETECTOR ACTIVE")
    logger.info("Press 'f' to trigger FIRE.")
    logger.info("Press 'a' to trigger ACCIDENT.")
    logger.info("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to grab frame.")
            break

        # Add Overlay
        cv2.putText(
            frame, 
            "SENTINEL AI - ACTIVE", 
            (20, 40), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1.0, 
            (0, 255, 0), 
            2
        )
        cv2.putText(
            frame, 
            "Press 'f': Fire | 'a': Accident | 'q': Quit", 
            (20, 80), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (255, 255, 255), 
            1
        )

        cv2.imshow("Sentinel AI", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('f'):
            logger.info("Triggering FIRE...")
            trigger_incident(camera, threats["FIRE"], "CRITICAL")
        elif key == ord('a'):
            logger.info("Triggering ACCIDENT...")
            trigger_incident(camera, threats["ACCIDENT"], "HIGH")
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


async def main():
    camera, threats = await setup_db_context()
    run_detector(camera, threats)


if __name__ == "__main__":
    asyncio.run(main())
