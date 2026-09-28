from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CameraRead(BaseModel):
    id: UUID
    name: str
    camera_type: str
    status: str
    latitude: float
    longitude: float
    fps: int

    model_config = ConfigDict(from_attributes=True)