import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.models.camera import Camera, CameraStatus


async def main():
    async with AsyncSessionFactory() as db:

        result = await db.execute(
            select(Camera).where(
                Camera.name == "Camera 1"
            )
        )

        camera = result.scalars().first()

        if camera is None:
            print("❌ Camera 1 not found.")
            return

        # Use laptop built-in webcam
        camera.rtsp_url = "0"

        # Enable camera
        camera.is_active = True

        # Show camera as online
        camera.status = CameraStatus.ONLINE

        await db.commit()
        await db.refresh(camera)

        print("=" * 50)
        print("Camera 1 configured successfully")
        print("=" * 50)
        print("Name      :", camera.name)
        print("RTSP URL  :", camera.rtsp_url)
        print("Status    :", camera.status.value)
        print("Active    :", camera.is_active)
        print("Latitude  :", camera.latitude)
        print("Longitude :", camera.longitude)
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())