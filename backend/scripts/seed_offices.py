import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionFactory
from app.models.emergency_office import EmergencyOffice
from sqlalchemy import text

OFFICES = [
    # Medical
    {"name": "Vijayanagara Institute of Medical Sciences (VIMS)", "type": "HOSPITAL", "lat": 15.1504, "lon": 76.9142, "phone": "+91 8392-235201"},
    {"name": "S.R. Multi Speciality Hospital", "type": "HOSPITAL", "lat": 15.1450, "lon": 76.9210, "phone": "+91 8392-273100"},
    {"name": "Nava Karnataka Hospital", "type": "HOSPITAL", "lat": 15.1520, "lon": 76.9180, "phone": "+91 8392-258900"},
    {"name": "Sai Health Care", "type": "HOSPITAL", "lat": 15.1390, "lon": 76.9120, "phone": "+91 8392-277500"},
    {"name": "M M Hospital", "type": "HOSPITAL", "lat": 15.1440, "lon": 76.9260, "phone": "+91 8392-244200"},
    {"name": "Danamma Hospital", "type": "HOSPITAL", "lat": 15.1475, "lon": 76.9150, "phone": "+91 8392-266300"},
    
    # Police
    {"name": "Rural Police HQ", "type": "POLICE", "lat": 15.1310, "lon": 76.9100, "phone": "+91 8392-275100"},
    {"name": "Cowl Bazaar Station", "type": "POLICE", "lat": 15.1550, "lon": 76.9250, "phone": "+91 8392-275200"},
    {"name": "S P Office", "type": "POLICE", "lat": 15.1400, "lon": 76.9050, "phone": "+91 8392-275300"},
    {"name": "Cantonment Station", "type": "POLICE", "lat": 15.1480, "lon": 76.9300, "phone": "+91 8392-275400"},
    {"name": "Women's Police Station", "type": "POLICE", "lat": 15.1425, "lon": 76.9185, "phone": "+91 8392-275500"},

    # Fire
    {"name": "Ballari Main Fire Station", "type": "FIRE", "lat": 15.1460, "lon": 76.9225, "phone": "+91 8392-255101"},
    {"name": "Fire Sub-Station North", "type": "FIRE", "lat": 15.1600, "lon": 76.9200, "phone": "+91 8392-255102"},
    {"name": "Fire Sub-Station South", "type": "FIRE", "lat": 15.1250, "lon": 76.9100, "phone": "+91 8392-255103"},
]

async def seed_offices():
    async with AsyncSessionFactory() as db:
        # Clear existing
        await db.execute(text("TRUNCATE TABLE emergency_offices CASCADE"))
        
        for office in OFFICES:
            new_office = EmergencyOffice(
                name=office["name"],
                office_type=office["type"],
                latitude=office["lat"],
                longitude=office["lon"],
                contact_number=office["phone"]
            )
            db.add(new_office)
        
        await db.commit()
        print(f"Successfully seeded {len(OFFICES)} high-accuracy Ballari emergency offices.")

if __name__ == "__main__":
    asyncio.run(seed_offices())
