"""
Sentinel — Pydantic Schemas for Incident API.

Request/response models used by the incidents router.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Nested Schemas ──────────────────────────────────────────────────

class ThreatTypeRead(BaseModel):
    """Minimal representation of a threat type embedded in incident responses."""
    id: uuid.UUID
    code: str
    name: str
    default_severity: str

    model_config = {"from_attributes": True}


# ── Incident Schemas ────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    """Payload accepted by ``POST /api/v1/incidents``."""

    incident_number: str = Field(
        ..., description="Human-readable incident ID, e.g. 'INC-20260426-0001'.",
    )
    camera_id: uuid.UUID
    zone_id: uuid.UUID
    threat_type_id: uuid.UUID
    severity: str = Field(..., description="CRITICAL | HIGH | MEDIUM | LOW")
    ai_confidence: float = Field(..., ge=0.0, le=1.0)
    ai_model_version: str = "sentinel-cv-v1"
    detected_at: datetime
    gps_latitude: float
    gps_longitude: float
    summary: Optional[str] = None


class IncidentRead(BaseModel):
    """Full incident representation returned by the API."""

    id: uuid.UUID
    incident_number: str
    camera_id: uuid.UUID
    zone_id: uuid.UUID
    threat_type_id: uuid.UUID
    severity: str
    status: str
    ai_confidence: float
    ai_model_version: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    gps_latitude: float
    gps_longitude: float
    summary: Optional[str] = None
    dispatched_offices: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    # Nested relationship (optional — populated when loaded)
    threat_type: Optional[ThreatTypeRead] = None

    model_config = {"from_attributes": True}


class IncidentAcknowledgeRequest(BaseModel):
    """Payload for acknowledging an incident from the dashboard."""
    notes: Optional[str] = None


class IncidentAcknowledgeResponse(BaseModel):
    """Confirmation returned after a successful acknowledgement."""
    incident_id: uuid.UUID
    status: str
    acknowledged_at: datetime
    message: str
