"""
Sentinel API package.
"""
from fastapi import APIRouter

from app.api.v1.incidents import router as incidents_router
from app.api.v1.stations import router as stations_router
from app.api.v1.cameras import router as cameras_router
from app.api.v1.detect import router as detect_router


api_v1_router = APIRouter()

api_v1_router.include_router(
    incidents_router,
    prefix="/incidents"
)

api_v1_router.include_router(
    stations_router,
    prefix="/stations"
)

api_v1_router.include_router(
    cameras_router,
    prefix="/cameras"
)

# Detection routes
api_v1_router.include_router(
    detect_router
)