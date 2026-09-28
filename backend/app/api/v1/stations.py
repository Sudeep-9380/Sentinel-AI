from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.emergency_office import EmergencyOffice
from app.schemas.emergency_office import EmergencyOfficeRead

router = APIRouter(tags=["Stations"])

@router.get("", response_model=list[EmergencyOfficeRead])
async def list_stations(
    db: AsyncSession = Depends(get_db),
):
    """Return all static emergency offices (stations)."""
    stmt = select(EmergencyOffice)
    result = await db.execute(stmt)
    stations = list(result.scalars().all())
    return stations
