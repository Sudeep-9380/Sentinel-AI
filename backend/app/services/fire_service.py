from ultralytics import YOLO

class FireService:

    def __init__(self):
        self.model = YOLO("app/ai_models/fire.pt")

    def detect(self, frame):

        results = self.model(frame, verbose=False)

        for result in results:

            for box in result.boxes:

                cls = int(box.cls[0])
                conf = float(box.conf[0])

                label = self.model.names[cls]

                if conf > 0.60:

                    return {
                        "incident": "Fire",
                        "confidence": round(conf,2),
                        "severity": "Critical",
                        "department": "Fire Department"
                    }

        return None