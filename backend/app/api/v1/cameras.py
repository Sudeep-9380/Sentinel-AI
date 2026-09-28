from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraRead

router = APIRouter(tags=["Cameras"])


@router.get("", response_model=list[CameraRead])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera))
    return list(result.scalars().all())