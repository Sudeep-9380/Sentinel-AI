"""
Sentinel — Incidents Router (API v1).

Endpoints:

    GET  /incidents
    GET  /incidents/{id}
    POST /incidents
    POST /incidents/{id}/acknowledge
    DELETE /incidents/{id}/dispatch/{department}
"""

from __future__ import annotations

import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db

from app.models.incident import (
    Incident,
    IncidentStatus,
    Severity,
    ThreatType,
)

from app.schemas.incident import (
    IncidentAcknowledgeRequest,
    IncidentAcknowledgeResponse,
    IncidentCreate,
    IncidentRead,
)

from app.services.dispatch_service import dispatch_service


router = APIRouter(tags=["Incidents"])


# ================================================================
# GET /incidents
# ================================================================

@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all active incidents, newest first.
    Deleted incidents are excluded.
    """

    stmt = (
        select(Incident)
        .options(selectinload(Incident.threat_type))
        .where(Incident.deleted_at.is_(None))
        .order_by(Incident.detected_at.desc())
        .limit(100)
    )

    result = await db.execute(stmt)

    incidents = list(result.scalars().all())

    return incidents


# ================================================================
# GET /incidents/{id}
# ================================================================

@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return a single active incident.
    """

    stmt = (
        select(Incident)
        .options(selectinload(Incident.threat_type))
        .where(
            Incident.id == incident_id,
            Incident.deleted_at.is_(None),
        )
    )

    result = await db.execute(stmt)

    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )

    return incident


# ================================================================
# POST /incidents
# ================================================================

@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new incident record.

    Called by the AI detector.
    """

    # ------------------------------------------------------------
    # Validate severity
    # ------------------------------------------------------------

    try:
        severity = Severity(payload.severity)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid severity: {payload.severity!r}. "
                "Must be one of: CRITICAL, HIGH, MEDIUM, LOW."
            ),
        )

    # ------------------------------------------------------------
    # Fetch threat type
    # ------------------------------------------------------------

    stmt_threat = select(ThreatType).where(
        ThreatType.id == payload.threat_type_id
    )

    result_threat = await db.execute(stmt_threat)

    threat_type = result_threat.scalar_one_or_none()

    # ------------------------------------------------------------
    # Find nearest responders
    # ------------------------------------------------------------

    try:

        dispatched_offices = (
            await dispatch_service.get_nearest_responders(
                db,
                payload.gps_latitude,
                payload.gps_longitude,
                threat_type.code
                if threat_type
                else "UNKNOWN",
            )
        )

    except Exception as e:

        print(
            f"PostGIS dispatch failed: {e}"
        )

        dispatched_offices = {}

    # ------------------------------------------------------------
    # Create incident
    # ------------------------------------------------------------

    incident = Incident(
        incident_number=payload.incident_number,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        threat_type_id=payload.threat_type_id,
        severity=severity,
        status=IncidentStatus.DETECTED,
        ai_confidence=payload.ai_confidence,
        ai_model_version=payload.ai_model_version,
        detected_at=payload.detected_at,
        gps_latitude=payload.gps_latitude,
        gps_longitude=payload.gps_longitude,
        summary=payload.summary,
        dispatched_offices=dispatched_offices,
    )

    db.add(incident)

    await db.commit()

    await db.refresh(incident)

    print(
        f"--- DATA SAVED: {incident.id} ---"
    )

    # ------------------------------------------------------------
    # Reload with threat type
    # ------------------------------------------------------------

    stmt = (
        select(Incident)
        .options(selectinload(Incident.threat_type))
        .where(Incident.id == incident.id)
    )

    result = await db.execute(stmt)

    incident = result.scalar_one()

    return incident


# ================================================================
# POST /incidents/{id}/acknowledge
# ================================================================

@router.post(
    "/{incident_id}/acknowledge",
    response_model=IncidentAcknowledgeResponse,
)
async def acknowledge_incident(
    incident_id: uuid.UUID,
    payload: IncidentAcknowledgeRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledge an incident.
    """

    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.deleted_at.is_(None),
    )

    result = await db.execute(stmt)

    incident = result.scalar_one_or_none()

    if not incident:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )

    if incident.status in (
        IncidentStatus.ACKNOWLEDGED,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    ):

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Incident already {incident.status.value}.",
        )

    now = datetime.now(timezone.utc)

    incident.status = IncidentStatus.ACKNOWLEDGED

    await db.commit()

    await db.refresh(incident)

    return IncidentAcknowledgeResponse(
        incident_id=incident.id,
        status=incident.status.value,
        acknowledged_at=now,
        message="Escalation timer cancelled. Incident acknowledged.",
    )


# ================================================================
# DELETE DEPARTMENT DISPATCH
# ================================================================

@router.delete(
    "/{incident_id}/dispatch/{department}",
    status_code=status.HTTP_200_OK,
)
async def delete_department_dispatch(
    incident_id: uuid.UUID,
    department: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove dispatch information for ONE department only.

    Examples:
        DELETE /incidents/{id}/dispatch/POLICE
        DELETE /incidents/{id}/dispatch/FIRE
        DELETE /incidents/{id}/dispatch/MEDICAL

    This does NOT delete the incident.
    """

    department = department.upper().strip()

    # These must exactly match the keys stored
    # inside incident.dispatched_offices.
    department_map = {
        "POLICE": "POLICE TEAM",
        "POLICE TEAM": "POLICE TEAM",

        "FIRE": "FIRE TEAM",
        "FIRE TEAM": "FIRE TEAM",

        "MEDICAL": "MEDICAL TEAM",
        "MEDICAL TEAM": "MEDICAL TEAM",
    }

    if department not in department_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department. Use POLICE, FIRE or MEDICAL.",
        )

    dispatch_key = department_map[department]

    # Find incident
    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.deleted_at.is_(None),
    )

    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found.",
        )

    # Copy existing JSON dispatch information
    dispatched_offices = (
        dict(incident.dispatched_offices)
        if incident.dispatched_offices
        else {}
    )

    # Already removed
    if dispatch_key not in dispatched_offices:
        return {
            "success": True,
            "message": f"No {dispatch_key} dispatch found.",
            "incident_id": str(incident_id),
            "department": dispatch_key,
        }

    # Remove only the requested department
    del dispatched_offices[dispatch_key]

    # Force SQLAlchemy to recognize JSON change
    incident.dispatched_offices = dispatched_offices

    await db.commit()
    await db.refresh(incident)

    print(
        f"--- {dispatch_key} DISPATCH REMOVED "
        f"FROM INCIDENT {incident_id} ---"
    )

    return {
        "success": True,
        "message": f"{dispatch_key} dispatch removed successfully.",
        "incident_id": str(incident_id),
        "department": dispatch_key,
    }