# Sentinel — AI Video Surveillance & Emergency Response System

## Backend Setup Guide (Windows Local Development)

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.11+ | [python.org/downloads](https://www.python.org/downloads/) |
| **PostgreSQL** | 15+ | [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) |
| **Memurai** | Latest | [memurai.com/get-memurai](https://www.memurai.com/get-memurai) (Redis for Windows) |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |

---

### 1. Clone & Install Dependencies

```powershell
cd C:\Users\Atiq\OneDrive\Documents\Sentinel\backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Configure Environment

```powershell
# Copy the example env file
Copy-Item .env.example .env

# Edit .env with your PostgreSQL credentials
# Default assumes: postgres/postgres on localhost:5432
```

Key variables to verify in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel
REDIS_URL=redis://localhost:6379/0
DRY_RUN=true
```

---

### 3. Create the PostgreSQL Database

Open **pgAdmin** or **psql** and run:

```sql
CREATE DATABASE sentinel;
```

Or via command line:

```powershell
psql -U postgres -c "CREATE DATABASE sentinel;"
```

---

### 4. Initialize Alembic (Database Migrations)

```powershell
# Initialize Alembic in the backend directory
alembic init alembic
```

Then edit `alembic.ini`:

```ini
# Replace the sqlalchemy.url line with:
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/sentinel
```

Edit `alembic/env.py` to use async and import the models:

```python
# At the top of alembic/env.py, add:
from app.models import Base
target_metadata = Base.metadata

# For async support, follow the Alembic async tutorial:
# https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
```

Generate and run the initial migration:

```powershell
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

---

### 5. Apply Immutability Triggers

After running `alembic upgrade head`, apply the database triggers.

Open the file `scripts/immutability_triggers.sql` in **pgAdmin** or **DBeaver** and execute it against the `sentinel` database.

Or via command line:

```powershell
psql -U postgres -d sentinel -f scripts\immutability_triggers.sql
```

**Verify the triggers work:**

```sql
-- This should raise an error:
-- "[SENTINEL] chain_of_custody_log is APPEND-ONLY..."
UPDATE chain_of_custody_log SET action = 'DELETED' WHERE id = gen_random_uuid();
```

---

### 6. Start Memurai (Redis)

Ensure Memurai is running (it typically runs as a Windows service after installation):

```powershell
# Check if Memurai is running
memurai-cli ping
# Expected response: PONG
```

---

### 7. Start the FastAPI Server

```powershell
# From the backend directory with venv activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify at: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

Expected response:

```json
{
  "status": "healthy",
  "service": "Sentinel",
  "environment": "development"
}
```

API docs available at: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

### 8. Start the Celery Worker

Open a **second terminal**, activate the venv, and run:

```powershell
cd C:\Users\Atiq\OneDrive\Documents\Sentinel\backend
.\venv\Scripts\Activate.ps1

# Start Celery worker (use --pool=solo on Windows)
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

> **Note:** Windows does not support Celery's default `prefork` pool.
> The `--pool=solo` flag is required for local Windows development.
> For production, deploy on Linux with the `prefork` or `gevent` pool.

---

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory + health check
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings (env vars)
│   │   ├── database.py          # Async SQLAlchemy engine + sessions
│   │   ├── dependencies.py      # FastAPI Depends (DB session)
│   │   └── security.py          # Auth stub (Phase 2)
│   ├── models/                  # SQLAlchemy ORM models (17 tables)
│   │   ├── base.py              # Declarative base + mixins
│   │   ├── zone.py              # Zone
│   │   ├── camera.py            # Camera
│   │   ├── incident.py          # ThreatType, Incident, IncidentDetection
│   │   ├── responder.py         # ResponderTier, Responder
│   │   ├── escalation.py        # EscalationRule, EscalationAction, Ack
│   │   ├── evidence.py          # EvidenceClip, EvidenceClipAccessLog
│   │   ├── notification.py      # NotificationLog
│   │   └── audit.py             # ChainOfCustodyLog, AuditLog, Playbooks
│   ├── schemas/                 # Pydantic request/response (Phase 1b)
│   ├── api/v1/                  # API endpoints (Phase 1b)
│   ├── services/                # Business logic (Phase 1b)
│   ├── repositories/            # Data access layer (Phase 1b)
│   └── workers/
│       ├── celery_app.py        # Celery configuration
│       └── escalation_tasks.py  # Escalation timer + notification tasks
├── scripts/
│   └── immutability_triggers.sql  # Run manually in pgAdmin/DBeaver
├── requirements.txt
├── .env.example
└── README.md                    # ← You are here
```

---

### Database Tables (17)

| # | Table | Description |
|---|-------|-------------|
| 1 | `zones` | Monitored geographic zones |
| 2 | `cameras` | RTSP camera feeds |
| 3 | `threat_types` | Detectable anomaly categories |
| 4 | `incidents` | Core AI-detected events |
| 5 | `incident_detections` | Per-frame bounding boxes & heatmaps |
| 6 | `responder_tiers` | T1–T4 escalation hierarchy |
| 7 | `responders` | Authorized responders with GPS |
| 8 | `escalation_rules` | Threat + severity → tier mapping |
| 9 | `escalation_actions` | Runtime escalation instances |
| 10 | `incident_acknowledgements` | Ack records with device/GPS info |
| 11 | `evidence_clips` | S3 video clips with SHA-256 hashes |
| 12 | `evidence_clip_access_log` | Append-only access audit |
| 13 | `chain_of_custody_log` | Hash-chained legal custody ledger |
| 14 | `notification_log` | FCM/SMS/Voice dispatch records |
| 15 | `automated_playbooks` | Response playbook definitions |
| 16 | `playbook_executions` | Playbook execution tracking |
| 17 | `audit_log` | System-wide event audit trail |

---

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `asyncpg` connection refused | Ensure PostgreSQL is running and accepting connections on port 5432 |
| `ModuleNotFoundError: celery` | Activate the virtual environment: `.\venv\Scripts\Activate.ps1` |
| Celery crashes on Windows | Always use `--pool=solo` on Windows |
| Memurai not responding | Start the Memurai service: `net start memurai` |
| Alembic can't find models | Ensure `from app.models import Base` is in `alembic/env.py` |
