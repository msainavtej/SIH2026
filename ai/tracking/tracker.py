import cv2
from ultralytics import YOLO

class ByteTracker:
    def __init__(self, model_path="yolov8n.pt", conf_threshold=0.5, classes=None):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.classes = classes if classes is not None else [0, 2, 3, 5, 7]
        
    def track(self, frame):
        """
        Run tracking on a frame. Returns a list of tracked objects with track_ids.
        """
        # persist=True enables tracking across frames
        results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", 
                                   conf=self.conf_threshold, classes=self.classes, verbose=False)
        
        tracked_objects = []
        for r in results:
            boxes = r.boxes
            if boxes.id is None:
                continue # No objects tracked in this frame
                
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                track_id = int(boxes.id[i].cpu().numpy())
                
                obj_type = self.model.names[cls_id]
                
                tracked_objects.append({
                    "track_id": f"{obj_type[0].upper()}{track_id}", # e.g. P1, C2
                    "object_type": obj_type,
                    "confidence": conf,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)]
                })
                
        return tracked_objects
