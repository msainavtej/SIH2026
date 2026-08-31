import cv2
from modules.gateway import StreamGateway
from modules.detector import EdgeDetector
from modules.event_engine import EventEngine
from modules.threat_engine import ThreatEngine
from modules.anpr_engine import ANPREngine
from modules.face_engine import FaceEngine
from modules.store_forward import StoreForwardQueue

class BorderXPipeline:
    def __init__(self, camera_id="CAM_01"):
        self.camera_id = camera_id
        self.detector = EdgeDetector(camera_id=camera_id)
        self.event_engine = EventEngine()
        self.threat_engine = ThreatEngine()
        self.anpr_engine = ANPREngine()
        self.face_engine = FaceEngine()
        self.queue = StoreForwardQueue()

    def process_frame(self, frame, is_night=True, correlated_cameras=None, is_online=False):
        # 1. Perception & Tracking
        detections = self.detector.detect_and_track(frame)
        
        # 2. Event Analysis (Perimeter, Dwell, Direction)
        events = self.event_engine.evaluate_events(detections, frame.shape, is_night=is_night)
        
        active_incidents = []

        for ev in events:
            det = ev["detection"]
            crop = det.get("crop")

            # 3. Secondary AI Verification Engines
            anpr_res = {"plate": None, "confidence": 0.0, "flag": "NOT_APPLICABLE"}
            face_res = {"candidate_match": None, "similarity": 0.0, "status": "NO_DETECTION"}

            if det["class_name"] == "vehicle":
                anpr_res = self.anpr_engine.extract_plate(crop)
            elif det["class_name"] == "person":
                face_res = self.face_engine.evaluate_face(crop)

            # 4. Threat Scoring & Explainable Rationale
            incident = self.threat_engine.evaluate_threat(ev, correlated_cameras=correlated_cameras)
            
            if incident:
                incident["anpr_data"] = anpr_res
                incident["face_data"] = face_res
                
                # 5. Offline Edge Queue Storage
                stored_incident = self.queue.enqueue_incident(incident, is_online=is_online)
                active_incidents.append(stored_incident)

        return detections, active_incidents