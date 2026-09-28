import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.emergency_office import EmergencyOffice


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.

    Returns distance in kilometers.
    """
    R = 6371.0

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class DispatchService:

    @staticmethod
    async def get_nearest_responders(
        db: AsyncSession,
        lat: float,
        lon: float,
        incident_type: str,
    ) -> dict:
        """
        Find the nearest emergency offices based on GPS location.

        Dispatch rules:

        FIRE
            -> Top 3 Fire Stations

        ACCIDENT / VEHICLE_ACCIDENT
            -> Top 3 Hospitals
            -> Top 3 Police Stations

        FIGHT / VIOLENCE / WEAPON / INTRUSION / THEFT / SUSPICIOUS
            -> Top 3 Police Stations

        Unknown incidents
            -> Top 1 Police Station
        """

        # ---------------------------------------------------------
        # Get all emergency offices
        # ---------------------------------------------------------

        stmt = select(EmergencyOffice)

        result = await db.execute(stmt)

        offices = result.scalars().all()

        # ---------------------------------------------------------
        # Separate offices by department
        # ---------------------------------------------------------

        hospitals = []
        police = []
        fire = []

        for office in offices:

            # Safety check for invalid GPS data
            if office.latitude is None or office.longitude is None:
                continue

            distance = haversine(
                lat,
                lon,
                office.latitude,
                office.longitude,
            )

            office_data = {
                "name": office.name,
                "office_type": office.office_type,
                "distance_km": round(distance, 2),
                "latitude": office.latitude,
                "longitude": office.longitude,
                "contact_number": office.contact_number,
            }

            office_type = str(office.office_type).upper()

            if office_type == "HOSPITAL":
                hospitals.append(office_data)

            elif office_type == "POLICE":
                police.append(office_data)

            elif office_type == "FIRE":
                fire.append(office_data)

        # ---------------------------------------------------------
        # Sort by nearest distance
        # ---------------------------------------------------------

        hospitals.sort(
            key=lambda x: x["distance_km"]
        )

        police.sort(
            key=lambda x: x["distance_km"]
        )

        fire.sort(
            key=lambda x: x["distance_km"]
        )

        # ---------------------------------------------------------
        # Normalize incident type
        # ---------------------------------------------------------

        incident_type = str(
            incident_type or ""
        ).upper().strip()

        # ---------------------------------------------------------
        # Department-specific dispatch
        # ---------------------------------------------------------

        grouped_dispatch = {}

        # =========================================================
        # FIRE
        # =========================================================

        if incident_type in (
            "FIRE",
            "FIRE_SMOKE",
        ):

            grouped_dispatch["FIRE TEAM"] = fire[:3]

        # =========================================================
        # ACCIDENT
        # =========================================================

        elif incident_type in (
            "ACCIDENT",
            "VEHICLE_ACCIDENT",
        ):

            grouped_dispatch["MEDICAL TEAM"] = hospitals[:3]

            grouped_dispatch["POLICE TEAM"] = police[:3]

        # =========================================================
        # POLICE INCIDENTS
        # =========================================================

        elif incident_type in (
            "FIGHT",
            "VIOLENCE",
            "WEAPON",
            "INTRUSION",
            "THEFT",
            "SHOPLIFTING",
            "SUSPICIOUS",
        ):

            grouped_dispatch["POLICE TEAM"] = police[:3]

        # =========================================================
        # UNKNOWN INCIDENT
        # =========================================================

        else:

            grouped_dispatch["POLICE TEAM"] = police[:1]

        return grouped_dispatch


dispatch_service = DispatchService()