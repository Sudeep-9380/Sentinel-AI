from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import Counter

import asyncio
import uuid

import cv2
from ultralytics import YOLO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory

from app.models.camera import Camera

from app.models.incident import (
    Incident,
    ThreatType,
    IncidentStatus,
    Severity,
)

from app.services.dispatch_service import DispatchService
from app.services.escalation_engine import EscalationEngine


class DetectionService:
    """
    Sentinel AI Detection Service

    Responsibilities
    ----------------
    • Run YOLO inference
    • Detect Fire / Accident / Fight / Theft
    • Process uploaded videos
    • Create incidents
    • Dispatch responders
    • Trigger escalation
    """

    def __init__(self):

        # =========================================================
        # LOAD YOLO MODEL
        # =========================================================

        model_path = (
            Path(__file__).resolve().parents[2]
            / "models"
            / "best.pt"
        )

        if not model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found: {model_path}"
            )

        self.model = YOLO(str(model_path))

        print("=" * 60)
        print("Sentinel AI Model Loaded")
        print("Model:", model_path)
        print("Classes:", self.model.names)
        print("=" * 60)

        # =========================================================
        # CONFIDENCE SETTINGS
        # =========================================================

        # Normal live detection
        self.min_confidence = 0.40

        # Uploaded video can use lower threshold
        # because we analyse multiple frames.
        self.video_confidence = 0.25

        # =========================================================
        # DUPLICATE INCIDENT COOLDOWN
        # =========================================================

        self.cooldown_seconds = 30

        # =========================================================
        # THREAT MAPPING
        # =========================================================

        self.threat_mapping = {
            "fire": {
                "code": "FIRE",
                "summary": "Fire detected",
                "severity": "CRITICAL",
                "police": True,
                "hospital": True,
            },

            "accident": {
                "code": "ACCIDENT",
                "summary": "Road accident detected",
                "severity": "CRITICAL",
                "police": True,
                "hospital": True,
            },

            "fight": {
                "code": "FIGHT",
                "summary": "Physical fight detected",
                "severity": "HIGH",
                "police": True,
                "hospital": True,
            },

            "theft": {
                "code": "THEFT",
                "summary": "Theft detected",
                "severity": "HIGH",
                "police": True,
                "hospital": False,
            },
        }

    # =============================================================
    # PROCESS FRAME
    # =============================================================

    def process_frame(
        self,
        frame,
        confidence_threshold: Optional[float] = None,
    ):

        if frame is None:
            return []

        if confidence_threshold is None:
            confidence_threshold = self.min_confidence

        try:

            results = self.model(
                frame,
                verbose=False,
                conf=confidence_threshold,
            )

        except Exception as error:

            print(
                "YOLO inference error:",
                error,
            )

            return []

        detections = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                confidence = float(
                    box.conf[0]
                )

                if (
                    confidence
                    < confidence_threshold
                ):
                    continue

                cls = int(
                    box.cls[0]
                )

                label = str(
                    self.model.names[cls]
                ).lower().strip()

                print(
                    f"YOLO Detection: "
                    f"{label} | "
                    f"{confidence:.2f}"
                )

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0],
                )

                detections.append(
                    {
                        "label": label,
                        "confidence": confidence,
                        "bbox": [
                            x1,
                            y1,
                            x2,
                            y2,
                        ],
                        "time": datetime.utcnow(),
                    }
                )

        return detections

    # =============================================================
    # DRAW BOXES
    # =============================================================

    def draw_boxes(
        self,
        frame,
        detections,
    ):

        COLORS = {
            "fire": (0, 0, 255),
            "smoke": (120, 120, 120),
            "accident": (255, 0, 0),
            "fight": (0, 165, 255),
            "theft": (0, 255, 255),
        }

        for detection in detections:

            x1, y1, x2, y2 = (
                detection["bbox"]
            )

            label = detection["label"]

            confidence = detection[
                "confidence"
            ]

            color = COLORS.get(
                label,
                (0, 255, 0),
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                2,
            )

            cv2.putText(
                frame,
                f"{label.upper()} "
                f"{confidence:.0%}",
                (x1, max(25, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        return frame

    # =============================================================
    # SAVE EVIDENCE
    # =============================================================

    def save_evidence(self, frame):

        evidence_dir = Path(
            "uploads/evidence"
        )

        evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"{uuid.uuid4()}.jpg"
        )

        filepath = (
            evidence_dir / filename
        )

        cv2.imwrite(
            str(filepath),
            frame,
        )

        return str(filepath)

    # =============================================================
    # COUNT OBJECTS
    # =============================================================

    def count_objects(
        self,
        detections,
    ):

        counts = {}

        for detection in detections:

            label = detection["label"]

            counts[label] = (
                counts.get(
                    label,
                    0,
                )
                + 1
            )

        return counts

    # =============================================================
    # DETECT THREAT
    # =============================================================

    def detect_threats(
        self,
        detections,
    ):

        if not detections:
            return None

        best = max(
            detections,
            key=lambda d: d[
                "confidence"
            ],
        )

        label = (
            best["label"]
            .lower()
            .strip()
        )

        if (
            label
            not in self.threat_mapping
        ):
            print(
                f"Ignored YOLO class: "
                f"{label}"
            )

            return None

        threat = self.threat_mapping[
            label
        ].copy()

        threat["confidence"] = (
            best["confidence"]
        )

        threat["bbox"] = (
            best["bbox"]
        )

        return threat

    # =============================================================
    # COOLDOWN
    # =============================================================

    def should_create_incident(
        self,
        last_incident_time:
        Optional[datetime],
    ):

        if last_incident_time is None:
            return True

        elapsed = (
            datetime.utcnow()
            - last_incident_time
        ).total_seconds()

        return (
            elapsed
            >= self.cooldown_seconds
        )

    # =============================================================
    # THREAT TYPE LOOKUP
    # =============================================================

    async def get_threat_type(
        self,
        db: AsyncSession,
        code: str,
    ) -> Optional[ThreatType]:

        result = await db.execute(
            select(ThreatType).where(
                ThreatType.code == code
            )
        )

        return (
            result.scalar_one_or_none()
        )

    # =============================================================
    # SAVE INCIDENT
    # =============================================================

    async def save_incident(
        self,
        db: AsyncSession,
        camera,
        threat,
        confidence,
        evidence_path,
    ):

        threat_type = (
            await self.get_threat_type(
                db,
                threat["code"],
            )
        )

        if threat_type is None:

            print(
                f"ThreatType "
                f"'{threat['code']}' "
                f"not found."
            )

            return None

        # =========================================================
        # DISPATCH
        # =========================================================

        dispatch_service = (
            DispatchService()
        )

        dispatched = (
            await dispatch_service
            .get_nearest_responders(
                db,
                camera.latitude,
                camera.longitude,
                threat["code"],
            )
        )

        # =========================================================
        # INCIDENT
        # =========================================================

        incident = Incident(

            incident_number=(
                "INC-"
                + datetime.utcnow()
                .strftime(
                    "%Y%m%d%H%M%S"
                )
            ),

            camera_id=camera.id,

            evidence_path=evidence_path,

            zone_id=camera.zone_id,

            threat_type_id=(
                threat_type.id
            ),

            severity=Severity(
                threat["severity"]
            ),

            status=(
                IncidentStatus.DETECTED
            ),

            ai_confidence=confidence,

            ai_model_version=(
                "Sentinel-YOLOv8-v1"
            ),

            detected_at=datetime.utcnow(),

            gps_latitude=(
                camera.latitude
            ),

            gps_longitude=(
                camera.longitude
            ),

            summary=(
                threat["summary"]
            ),

            dispatched_offices=(
                dispatched
            ),
        )

        db.add(incident)

        await db.commit()

        await db.refresh(
            incident
        )

        print("=" * 60)
        print(
            "INCIDENT SAVED"
        )
        print(
            "Incident:",
            incident.incident_number,
        )
        print(
            "Threat:",
            threat["code"],
        )
        print(
            "Confidence:",
            confidence,
        )
        print(
            "GPS:",
            camera.latitude,
            camera.longitude,
        )
        print(
            "Dispatch:",
            dispatched,
        )
        print("=" * 60)

        return incident

    # =============================================================
    # PROCESS UPLOADED VIDEO
    # =============================================================

    async def process_uploaded_video(
        self,
        video_path: str,
    ):

        print("=" * 60)
        print(
            "STARTING UPLOADED VIDEO"
        )
        print(
            "Video:",
            video_path,
        )
        print("=" * 60)

        cap = cv2.VideoCapture(
            video_path
        )

        if not cap.isOpened():

            raise Exception(
                "Unable to open uploaded video."
            )

        detections_result = []

        class_counter = Counter()

        confidence_sum = {}

        frame_number = 0

        total_frames = int(
            cap.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        fps = cap.get(
            cv2.CAP_PROP_FPS
        )

        print(
            f"Total frames: "
            f"{total_frames}"
        )

        print(
            f"FPS: {fps}"
        )

        try:

            while True:

                success, frame = (
                    cap.read()
                )

                if not success:
                    break

                frame_number += 1

                # =================================================
                # CHECK EVERY 2ND FRAME
                # =================================================

                if (
                    frame_number % 2 != 0
                ):
                    continue

                # =================================================
                # DO NOT DISTORT VIDEO
                # YOLO handles resizing internally
                # =================================================

                detections = (
                    self.process_frame(
                        frame,
                        confidence_threshold=(
                            self.video_confidence
                        ),
                    )
                )

                if not detections:

                    continue

                # =================================================
                # DETECT THREAT
                # =================================================

                threat = (
                    self.detect_threats(
                        detections
                    )
                )

                if threat is None:

                    continue

                label = (
                    threat["code"]
                    .lower()
                )

                class_counter[
                    label
                ] += 1

                confidence_sum[
                    label
                ] = (
                    confidence_sum.get(
                        label,
                        0,
                    )
                    + threat[
                        "confidence"
                    ]
                )

                detections_result.append(
                    {
                        "frame": frame_number,
                        "incident": threat,
                        "detections": detections,
                    }
                )

                print(
                    f"VIDEO FRAME "
                    f"{frame_number}: "
                    f"{threat['code']} "
                    f"{threat['confidence']:.2%}"
                )

        finally:

            cap.release()

        # =========================================================
        # NO DETECTION
        # =========================================================

        if not detections_result:

            print("=" * 60)
            print(
                "NO INCIDENT DETECTED"
            )
            print(
                "Model classes:",
                self.model.names,
            )
            print(
                "Confidence threshold:",
                self.video_confidence,
            )
            print("=" * 60)

            return []

        # =========================================================
        # SELECT FINAL CLASS USING AVERAGE CONFIDENCE
        # =========================================================
        #
        # For uploaded videos, do not select the class only by
        # frame frequency. A class can appear in more frames because
        # of occasional false detections. We instead calculate the
        # average confidence for each class and select the class
        # with the strongest average confidence.
        # =========================================================

        average_confidence = {}

        for label, total_confidence in confidence_sum.items():

            count = class_counter.get(label, 0)

            if count > 0:
                average_confidence[label] = (
                    total_confidence / count
                )

        if not average_confidence:

            print("=" * 60)
            print(
                "NO VALID THREAT CLASS FOUND"
            )
            print("=" * 60)

            return []

        final_label = max(
            average_confidence,
            key=average_confidence.get,
        )

        # =========================================================
        # BEST DETECTION FOR FINAL CLASS
        # =========================================================

        candidates = [
            detection
            for detection
            in detections_result
            if detection[
                "incident"
            ]["code"].lower()
            == final_label
        ]

        if not candidates:

            print("=" * 60)
            print(
                "NO CANDIDATE FOUND FOR FINAL CLASS:",
                final_label,
            )
            print("=" * 60)

            return []

        best = max(
            candidates,
            key=lambda x: x[
                "incident"
            ]["confidence"],
        )

        print("=" * 60)
        print(
            "VIDEO DETECTION RESULT"
        )
        print(
            "Class Counter:",
            dict(class_counter),
        )
        print(
            "Confidence Sum:",
            confidence_sum,
        )
        print(
            "Average Confidence:",
            average_confidence,
        )
        print(
            "Final Label:",
            final_label,
        )
        print(
            "Confidence:",
            best[
                "incident"
            ]["confidence"],
        )
        print("=" * 60)

        # =========================================================
        # CREATE DATABASE INCIDENT
        # =========================================================

        created_incident = (
            await self.create_incident(
                final_label,
                best[
                    "incident"
                ]["severity"],
                best[
                    "incident"
                ]["confidence"],
            )
        )

        # =========================================================
        # ADD DATABASE INFORMATION
        # =========================================================

        if created_incident:

            best["incident"][
                "gps_latitude"
            ] = (
                float(
                    created_incident
                    .gps_latitude
                )
                if (
                    created_incident
                    .gps_latitude
                    is not None
                )
                else None
            )

            best["incident"][
                "gps_longitude"
            ] = (
                float(
                    created_incident
                    .gps_longitude
                )
                if (
                    created_incident
                    .gps_longitude
                    is not None
                )
                else None
            )

            best["incident"][
                "incident_id"
            ] = str(
                created_incident.id
            )

            best["incident"][
                "incident_number"
            ] = (
                created_incident
                .incident_number
            )

            print("=" * 60)
            print(
                "INCIDENT CREATED SUCCESSFULLY"
            )
            print(
                "Incident Number:",
                created_incident
                .incident_number,
            )
            print(
                "GPS:",
                created_incident
                .gps_latitude,
                created_incident
                .gps_longitude,
            )
            print("=" * 60)

        else:

            print(
                "WARNING: "
                "Incident was not saved."
            )

            best["incident"][
                "gps_latitude"
            ] = None

            best["incident"][
                "gps_longitude"
            ] = None

            best["incident"][
                "incident_id"
            ] = None

            best["incident"][
                "incident_number"
            ] = None

        return [best]

    # =============================================================
    # CREATE INCIDENT
    # =============================================================

    async def create_incident(
        self,
        label,
        severity,
        confidence,
    ):

        print("=" * 60)
        print(
            "Creating Incident..."
        )
        print(
            "Label:",
            label,
        )
        print(
            "Severity:",
            severity,
        )
        print(
            "Confidence:",
            confidence,
        )
        print("=" * 60)

        async with (
            AsyncSessionFactory()
            as session
        ):

            # =====================================================
            # CAMERA 1
            # =====================================================

            camera_result = (
                await session.execute(
                    select(Camera).where(
                        Camera.name
                        == "Camera 1"
                    )
                )
            )

            camera = (
                camera_result
                .scalars()
                .first()
            )

            if camera is None:

                print(
                    "ERROR: "
                    "Camera 1 not found."
                )

                return None

            # =====================================================
            # THREAT TYPE
            # =====================================================

            threat_result = (
                await session.execute(
                    select(
                        ThreatType
                    ).where(
                        ThreatType.code
                        == label.upper()
                    )
                )
            )

            threat = (
                threat_result
                .scalars()
                .first()
            )

            if threat is None:

                print(
                    f"ERROR: "
                    f"ThreatType "
                    f"'{label.upper()}' "
                    f"not found."
                )

                return None

            # =====================================================
            # THREAT DATA
            # =====================================================

            threat_data = {
                "code": threat.code,
                "summary": (
                    f"{label.upper()} "
                    "detected automatically"
                ),
                "severity": severity,
            }

            # =====================================================
            # SAVE INCIDENT
            # =====================================================

            incident = (
                await self.save_incident(
                    session,
                    camera,
                    threat_data,
                    confidence,
                    None,
                )
            )

            if incident is None:

                print(
                    "ERROR: "
                    "Incident not saved."
                )

                return None

            print("=" * 60)
            print(
                "INCIDENT SAVED SUCCESSFULLY"
            )
            print(
                "Incident Number:",
                incident.incident_number,
            )
            print(
                "Incident ID:",
                incident.id,
            )
            print(
                "Latitude:",
                incident.gps_latitude,
            )
            print(
                "Longitude:",
                incident.gps_longitude,
            )
            print("=" * 60)

            return incident