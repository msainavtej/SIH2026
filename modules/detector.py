import cv2
import numpy as np
from ultralytics import YOLO

class EdgeDetector:
    def __init__(self, model_path="yolov8n.pt", camera_id="CAM_01"):
        self.model = YOLO(model_path)
        self.camera_id = camera_id
        # COCO class map: 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck, 14-23: animals
        self.animal_classes = {14, 15, 16, 17, 18, 19, 20, 21, 22, 23}

    def detect_and_track(self, frame):
        results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        detection_objects = []

        if not results or not results[0].boxes or results[0].boxes.id is None:
            return detection_objects

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        confidences = results[0].boxes.conf.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)

        h, w = frame.shape[:2]

        for bbox, track_id, conf, cls_id in zip(boxes, track_ids, confidences, class_ids):
            x1, y1, x2, y2 = map(int, bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            if cls_id == 0:
                class_name = "person"
            elif cls_id in {2, 3, 5, 7}:
                class_name = "vehicle"
            elif cls_id in self.animal_classes:
                class_name = "animal"
            else:
                continue

            cx = (x1 + x2) // 2
            crop = frame[y1:y2, x1:x2].copy()

            # Output adhering directly to core detection contract schema[cite: 3]
            detection_objects.append({
                "camera_id": self.camera_id,
                "track_id": int(track_id),
                "class_name": class_name,
                "confidence": float(conf),
                "bbox": [x1, y1, x2, y2],
                "foot_point": (int(cx), int(y2)),
                "crop": crop
            })

        return detection_objects
