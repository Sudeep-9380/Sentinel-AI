from __future__ import annotations
import uuid
from pydantic import BaseModel, ConfigDict

class EmergencyOfficeRead(BaseModel):
    id: uuid.UUID
    name: str
    office_type: str
    latitude: float
    longitude: float
    contact_number: str | None = None

    model_config = ConfigDict(from_attributes=True)
