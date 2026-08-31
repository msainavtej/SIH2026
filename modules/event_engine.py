import cv2
import numpy as np
import time
from config.settings import ZONES, DWELL_TIME_THRESHOLD_SEC

class EventEngine:
    def __init__(self):
        # track_id -> {"first_seen": timestamp, "last_seen": timestamp, "past_points": []}
        self.track_history = {}

    def is_in_polygon(self, point, polygon_norm, frame_shape):
        h, w = frame_shape[:2]
        pts = np.array([[int(x * w), int(y * h)] for x, y in polygon_norm], dtype=np.int32)
        return cv2.pointPolygonTest(pts, (float(point[0]), float(point[1])), False) >= 0

    def check_fence_crossing(self, past_points, fence_line_norm, frame_shape):
        """Checks if trajectory crossed the horizontal virtual fence line."""
        if len(past_points) < 2:
            return False
        h, _ = frame_shape[:2]
        fence_y = int(fence_line_norm[0][1] * h)
        y_prev = past_points[-2][1]
        y_curr = past_points[-1][1]
        return (y_prev < fence_y <= y_curr) or (y_curr < fence_y <= y_prev)

    def evaluate_events(self, detection_objects, frame_shape, is_night=True):
        events = []
        current_time = time.time()

        for obj in detection_objects:
            tid = obj["track_id"]
            foot = obj["foot_point"]

            if tid not in self.track_history:
                self.track_history[tid] = {
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "past_points": [foot]
                }
            else:
                self.track_history[tid]["last_seen"] = current_time
                self.track_history[tid]["past_points"].append(foot)

            history = self.track_history[tid]
            dwell_time = current_time - history["first_seen"]

            in_restricted = self.is_in_polygon(foot, ZONES["RESTRICTED_SECTOR"], frame_shape)
            fence_crossed = self.check_fence_crossing(history["past_points"], ZONES["VIRTUAL_FENCE_LINE"], frame_shape)

            events.append({
                "detection": obj,
                "in_restricted": in_restricted,
                "fence_crossed": fence_crossed,
                "is_night": is_night,
                "dwell_time": dwell_time,
                "is_loitering": dwell_time >= DWELL_TIME_THRESHOLD_SEC
            })

        return events