"""
Sentinel — Model Registry.

All SQLAlchemy ORM models are imported here so that:
1. Alembic can auto-discover them for migration generation.
2. Relationship back-references resolve correctly at import time.

Usage::

    from app.models import Base  # For Alembic target_metadata
    from app.models import Incident, EscalationRule  # For service code
"""

from app.models.base import Base  # noqa: F401

# Domain models — import order follows foreign-key dependency graph
from app.models.zone import Zone, ZoneType  # noqa: F401
from app.models.camera import Camera, CameraStatus, CameraType  # noqa: F401
from app.models.incident import (  # noqa: F401
    IncidentDetection,
    IncidentStatus,
    Incident,
    Severity,
    ThreatType,
)
from app.models.emergency_office import EmergencyOffice  # noqa: F401
from app.models.responder import Responder, ResponderTier  # noqa: F401
from app.models.escalation import (  # noqa: F401
    EscalationAction,
    EscalationRule,
    EscalationStatus,
    IncidentAcknowledgement,
)
from app.models.evidence import (  # noqa: F401
    ActorType,
    EvidenceAccessAction,
    EvidenceClip,
    EvidenceClipAccessLog,
    EvidenceStatus,
)
from app.models.notification import (  # noqa: F401
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
)
from app.models.audit import (  # noqa: F401
    AuditActorType,
    AuditLog,
    AutomatedPlaybook,
    ChainOfCustodyLog,
    CustodyAction,
    CustodyActorType,
    PlaybookExecution,
    PlaybookStatus,
)
