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
    Return all non-deleted incidents, newest first.
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
    Return one non-deleted incident.
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
    Remove dispatch information for ONE department.

    Supported:

        POLICE
        POLICE TEAM
        FIRE
        FIRE TEAM
        MEDICAL
        MEDICAL TEAM

    After removing the selected department:

    - The department disappears from dispatched_offices.
    - The department dashboard will no longer receive that incident.
    - If no dispatches remain, the incident is soft-deleted.
    """

    # ============================================================
    # NORMALIZE DEPARTMENT
    # ============================================================

    department = (
        department
        .upper()
        .strip()
        .replace("_", " ")
        .replace("-", " ")
    )

    # Convert multiple spaces to one
    department = " ".join(
        department.split()
    )


    # ============================================================
    # DEPARTMENT ALIASES
    # ============================================================

    department_aliases = {

        "POLICE": [
            "POLICE",
            "POLICE TEAM",
        ],

        "FIRE": [
            "FIRE",
            "FIRE TEAM",
        ],

        "MEDICAL": [
            "MEDICAL",
            "MEDICAL TEAM",
            "HOSPITAL",
        ],
    }


    if department not in department_aliases:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid department. "
                "Use POLICE, FIRE or MEDICAL."
            ),
        )


    possible_keys = department_aliases[
        department
    ]


    # ============================================================
    # FIND INCIDENT
    # ============================================================

    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.deleted_at.is_(None),
    )

    result = await db.execute(stmt)

    incident = result.scalar_one_or_none()


    if not incident:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Incident {incident_id} "
                f"not found."
            ),
        )


    # ============================================================
    # GET CURRENT DISPATCH DATA
    # ============================================================

    dispatched_offices = (
        dict(
            incident.dispatched_offices
        )
        if incident.dispatched_offices
        else {}
    )


    print(
        "CURRENT DISPATCH DATA:",
        dispatched_offices
    )


    # ============================================================
    # FIND ACTUAL KEY
    #
    # Handles:
    #
    # POLICE
    # POLICE TEAM
    # FIRE
    # FIRE TEAM
    # MEDICAL
    # MEDICAL TEAM
    # ============================================================

    actual_key = None


    for key in possible_keys:

        if key in dispatched_offices:

            actual_key = key

            break


    # Also perform case-insensitive
    # matching for safety.

    if actual_key is None:

        for existing_key in list(
            dispatched_offices.keys()
        ):

            normalized_existing_key = (
                str(existing_key)
                .upper()
                .strip()
            )

            for key in possible_keys:

                if (
                    normalized_existing_key
                    == key
                ):

                    actual_key = existing_key

                    break

            if actual_key is not None:
                break


    # ============================================================
    # DISPATCH NOT FOUND
    # ============================================================

    if actual_key is None:

        return {
            "success": True,

            "message": (
                f"No {department} "
                f"dispatch found."
            ),

            "incident_id": str(
                incident_id
            ),

            "department": department,

            "incident_deleted": False,

            "remaining_dispatches": (
                list(
                    dispatched_offices.keys()
                )
            ),
        }


    # ============================================================
    # REMOVE DEPARTMENT
    # ============================================================

    print(
        f"--- REMOVING DISPATCH --- "
        f"{actual_key}"
    )

    del dispatched_offices[
        actual_key
    ]


    # ============================================================
    # UPDATE INCIDENT
    # ============================================================

    incident.dispatched_offices = (
        dispatched_offices
    )


    # ============================================================
    # CHECK REMAINING DISPATCHES
    # ============================================================

    incident_deleted = False


    if not dispatched_offices:

        incident.deleted_at = (
            datetime.now(timezone.utc)
        )

        incident.status = (
            IncidentStatus.RESOLVED
        )

        incident_deleted = True

        print(
            "--- INCIDENT SOFT DELETED ---",
            incident_id,
        )


    # ============================================================
    # SAVE TO DATABASE
    # ============================================================

    await db.commit()

    await db.refresh(
        incident
    )


    # ============================================================
    # LOG
    # ============================================================

    print(
        f"--- {department} DISPATCH "
        f"REMOVED ---"
    )

    print(
        "INCIDENT:",
        incident_id
    )

    print(
        "REMOVED KEY:",
        actual_key
    )

    print(
        "REMAINING DISPATCHES:",
        incident.dispatched_offices
    )


    # ============================================================
    # RESPONSE
    # ============================================================

    return {

        "success": True,

        "message": (
            f"{department} dispatch "
            f"removed successfully."
        ),

        "incident_id": str(
            incident_id
        ),

        "department": department,

        "removed_key": actual_key,

        "incident_deleted": (
            incident_deleted
        ),

        "remaining_dispatches": (
            list(
                incident
                .dispatched_offices
                .keys()
            )
            if incident.dispatched_offices
            else []
        ),
    }