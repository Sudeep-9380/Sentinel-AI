import sys
import os
import asyncio
import uuid
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select

from app.core.database import engine
from app.models.incident import Incident, Severity
from app.models.camera import Camera
from app.models.zone import Zone
from app.models.incident import ThreatType

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def seed():
    async with AsyncSessionLocal() as db:
        try:
            # get existing data
            camera = (await db.execute(select(Camera))).scalars().first()
            zone = (await db.execute(select(Zone))).scalars().first()
            threat = (await db.execute(
                select(ThreatType).where(ThreatType.code == "ACCIDENT")
            )).scalars().first()

            if not camera or not zone or not threat:
                print("❌ Missing base data")
                return

            incident = Incident(
                id=uuid.uuid4(),
                incident_number="INC-0001",
                camera_id=camera.id,
                zone_id=zone.id,
                threat_type_id=threat.id,
                severity=Severity.HIGH,
                ai_confidence=0.95,
                ai_model_version="v1",
                detected_at=datetime.utcnow(),
                gps_latitude=15.1394,
                gps_longitude=76.9242,
                summary="Test incident"
            )

            db.add(incident)
            await db.commit()

            print("✅ Incident seeded!")

        except Exception as e:
            await db.rollback()
            print("❌ Error:", e)

if __name__ == "__main__":
    asyncio.run(seed())