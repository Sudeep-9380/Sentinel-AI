
import sys
import os
import asyncio
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models.zone import Zone
from app.models.camera import Camera

# Create async session
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def seed():
    async with AsyncSessionLocal() as db:

        # -------- ZONES --------
        zone1 = Zone(
            id=uuid.uuid4(),
            name="Zone A",
            zone_type="OUTDOOR",
            latitude=15.1394,
            longitude=76.9242
            
        )

        zone2 = Zone(
            id=uuid.uuid4(),
            name="Zone B",
            zone_type="OUTDOOR",
            latitude=15.1450,
            longitude=76.9200
            
        )

        # -------- CAMERAS --------
        camera1 = Camera(
            id=uuid.uuid4(),
            name="Camera 1",
            rtsp_url="0",
            camera_type="FIXED",
            status="OFFLINE",
            zone_id=zone1.id,
            latitude=15.1394,
            longitude=76.9242,
            resolution_width=1920,
            resolution_height=1080,
            fps=30
        )

        camera2 = Camera(
            id=uuid.uuid4(),
            name="Camera 2",
            rtsp_url="0",
            camera_type="FIXED",
            status="OFFLINE",
            zone_id=zone2.id,
            latitude=15.1450,
            longitude=76.9200,
            resolution_width=1920,
            resolution_height=1080,
            fps=30
        )

        try:
            from sqlalchemy import text

            # Clear old data
            await db.execute(text("DELETE FROM cameras"))
            await db.execute(text("DELETE FROM zones"))
            # Add new
            db.add_all([zone1, zone2, camera1, camera2])

            await db.commit()
            print("✅ Async seed completed!")

        except Exception as e:
            await db.rollback()
            print("❌ Error:", e)

# Run async
if __name__ == "__main__":
    asyncio.run(seed())