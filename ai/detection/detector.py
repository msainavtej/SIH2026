import cv2
import numpy as np
from ultralytics import YOLO
from backend.schemas.events import TrackedObject

class ObjectDetector:
    def __init__(self, model_path="yolov8n.pt", conf_threshold=0.5, classes=None):
        """
        Initialize the YOLO object detector.
        By default, we might only want to detect persons (class 0) and vehicles (classes 2, 3, 5, 7 in COCO).
        """
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        # Default to person (0), car (2), motorcycle (3), bus (5), truck (7)
        self.classes = classes if classes is not None else [0, 2, 3, 5, 7]
        
    def detect(self, frame) -> list:
        """
        Run detection on a single frame.
        Returns a list of dicts or TrackedObject (we can use raw dicts here and convert later).
        """
        results = self.model(frame, conf=self.conf_threshold, classes=self.classes, verbose=False)
        
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                # Map COCO class ID to string
                obj_type = self.model.names[cls_id]
                
                detections.append({
                    "object_type": obj_type,
                    "confidence": conf,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                })
                
        return detections
