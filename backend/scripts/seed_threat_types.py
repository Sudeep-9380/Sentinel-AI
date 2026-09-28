def detect_threats(self, detections):

    labels = [d["label"] for d in detections]

    # ------------------------
    # Violence
    # ------------------------

    if "person" in labels and "knife" in labels:

        return {
            "code": "VIOLENCE",
            "severity": "CRITICAL",
            "summary": "Person carrying a knife detected."
        }

    # ------------------------
    # Fire
    # ------------------------

    if "fire hydrant" in labels:

        return {
            "code": "FIRE",
            "severity": "CRITICAL",
            "summary": "Possible fire detected."
        }

    # ------------------------
    # Crowd
    # ------------------------

    if labels.count("person") >= 10:

        return {
            "code": "SUSPICIOUS",
            "severity": "MEDIUM",
            "summary": "Large crowd detected."
        }

    return None