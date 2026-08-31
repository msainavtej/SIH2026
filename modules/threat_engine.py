from datetime import datetime
from config.settings import RISK_WEIGHTS

class ThreatEngine:
    def evaluate_threat(self, event_data, correlated_cameras=None):
        det = event_data["detection"]
        target_class = det["class_name"]

        # Animals do not trigger critical human intrusion alerts
        if target_class == "animal":
            return None

        zone_risk = 0
        night_risk = 0
        fence_breach_risk = 0
        cross_camera_risk = 0
        reasons = []

        # 1. Zone Risk
        if event_data["in_restricted"]:
            zone_risk = RISK_WEIGHTS["RESTRICTED_ZONE"]
            reasons.append("Restricted Zone breach")
        else:
            zone_risk = RISK_WEIGHTS["NORMAL_ZONE"]

        # 2. Time Risk
        if event_data["is_night"]:
            night_risk = RISK_WEIGHTS["NIGHT_MOVEMENT"]
            reasons.append("Night movement")

        # 3. Movement / Perimeter Risk
        if event_data["fence_crossed"]:
            fence_breach_risk = RISK_WEIGHTS["FENCE_BREACH"]
            reasons.append("Virtual fence crossed")

        # 4. Cross-Camera Correlation Risk
        if correlated_cameras and len(correlated_cameras) > 0:
            cross_camera_risk = RISK_WEIGHTS["CROSS_CAMERA_MATCH"]
            reasons.append(f"{len(correlated_cameras) + 1}-camera confirmation")

        total_score = min(100, zone_risk + night_risk + fence_breach_risk + cross_camera_risk)

        if total_score >= 76:
            severity = "CRITICAL"
        elif total_score >= 51:
            severity = "MEDIUM"
        elif total_score >= 26:
            severity = "LOW"
        else:
            severity = "INFORMATION"

        rationale = " + ".join(reasons) if reasons else "Routine background movement"

        # Incident contract structure
        return {
            "incident_id": f"INC_{int(datetime.utcnow().timestamp())}_{det['track_id']}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "primary_camera": det["camera_id"],
            "correlated_cameras": correlated_cameras or [],
            "track_id": det["track_id"],
            "target_class": target_class,
            "threat_score": total_score,
            "severity": severity,
            "rationale": rationale,
            "rule_breakdown": {
                "zone_risk": zone_risk,
                "night_risk": night_risk,
                "fence_breach_risk": fence_breach_risk,
                "cross_camera_risk": cross_camera_risk
            },
            "anpr_data": {"plate": None, "confidence": 0.0, "flag": "NOT_APPLICABLE"},
            "face_data": {"candidate_match": None, "similarity": 0.0, "status": "NO_MATCH"},
            "evidence_clip": "",
            "sync_status": "QUEUED_LOCAL",
            "acknowledged_by": None
        }