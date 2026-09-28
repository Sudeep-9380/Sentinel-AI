from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
)

from pathlib import Path

import shutil
import cv2
import os

from app.services.detection_service import (
    DetectionService,
)


router = APIRouter(
    prefix="/detect",
    tags=["Detection"],
)

detector = DetectionService()

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True,
)


# ============================================================
# IMAGE DETECTION
# ============================================================

@router.post("/image")
async def detect_image(
    file: UploadFile = File(...)
):

    upload_dir = Path(
        "uploads/images"
    )

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        upload_dir / file.filename
    )

    with open(
        file_path,
        "wb",
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer,
        )

    frame = cv2.imread(
        str(file_path)
    )

    if frame is None:

        raise HTTPException(
            status_code=400,
            detail="Invalid image.",
        )

    detections = (
        detector.process_frame(
            frame,
            confidence_threshold=0.25,
        )
    )

    threat = (
        detector.detect_threats(
            detections
        )
    )

    return {
        "success": True,
        "filename": file.filename,
        "count": len(detections),
        "detected": (
            threat is not None
        ),
        "threat": threat,
        "detections": detections,
    }


# ============================================================
# UPLOADED VIDEO DETECTION
# ============================================================

@router.post("/video")
async def detect_video(
    file: UploadFile = File(...)
):

    upload_dir = Path(
        "uploads/videos"
    )

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Prevent problematic filenames

    safe_filename = Path(
        file.filename
    ).name

    file_path = (
        upload_dir / safe_filename
    )

    try:

        with open(
            file_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        print("=" * 60)
        print(
            "Uploaded video:",
            file_path,
        )
        print("=" * 60)

        results = (
            await detector
            .process_uploaded_video(
                str(file_path)
            )
        )

        if not results:

            return {
                "success": True,
                "detected": False,
                "incident_created": False,
                "frames_detected": 0,
                "results": [],
                "message": (
                    "No incident detected "
                    "in uploaded video."
                ),
            }

        best_result = results[0]

        incident = (
            best_result.get(
                "incident"
            )
            or {}
        )

        return {
            "success": True,

            "detected": True,

            "incident_created": (
                incident.get(
                    "incident_id"
                )
                is not None
            ),

            "frames_detected": len(
                results
            ),

            "threat": incident,

            "results": results,

            "message": (
                f"{incident.get('code', 'INCIDENT')} "
                "detected successfully."
            ),
        }

    except Exception as error:

        print(
            "=" * 60
        )

        print(
            "VIDEO DETECTION ERROR:",
            error,
        )

        print(
            "=" * 60
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# LIVE CAMERA FRAME DETECTION
# ============================================================

@router.post("/frame")
async def detect_frame(
    file: UploadFile = File(...)
):

    upload_dir = Path(
        "uploads/live"
    )

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = (
        upload_dir / "camera1.jpg"
    )

    try:

        with open(
            file_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        frame = cv2.imread(
            str(file_path)
        )

        if frame is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid camera frame."
                ),
            )

        detections = (
            detector.process_frame(
                frame,
                confidence_threshold=0.40,
            )
        )

        if not detections:

            return {
                "detected": False,
                "detections": [],
                "threat": None,
                "incident_created": False,
                "incident": None,
            }

        threat = (
            detector.detect_threats(
                detections
            )
        )

        if threat is None:

            return {
                "detected": False,
                "detections": detections,
                "threat": None,
                "incident_created": False,
                "incident": None,
            }

        return {
            "detected": True,
            "detections": detections,
            "threat": threat,
            "incident_created": False,
            "incident": None,
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            "Live frame detection error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# DIRECT OPENCV LIVE CAMERA
# ============================================================

@router.get("/live")
async def live_detection():

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to open webcam."
            ),
        )

    try:

        while True:

            success, frame = (
                cap.read()
            )

            if not success:
                break

            detections = (
                detector.process_frame(
                    frame,
                    confidence_threshold=0.40,
                )
            )

            frame = (
                detector.draw_boxes(
                    frame,
                    detections,
                )
            )

            cv2.imshow(
                "Sentinel AI",
                frame,
            )

            if (
                cv2.waitKey(1)
                == ord("q")
            ):
                break

    finally:

        cap.release()

        cv2.destroyAllWindows()

    return {
        "status":
            "Live Detection Stopped"
    }