import cv2
import time
import numpy as np
from camera.base import CameraSource

class SimulatedCamera(CameraSource):
    def __init__(self, camera_id: str, fps: int = 15):
        super().__init__(camera_id)
        self.target_fps = fps

    def connect(self):
        self.status = "ONLINE"
        self.is_running = True
        self.fps = self.target_fps
        self.last_error = ""

    def read(self):
        if not self.is_running:
            return False, None
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"CAM: {self.camera_id}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        time.sleep(1.0 / self.target_fps)
        self.frames_received += 1
        self.last_frame_time = time.time()
        return True, frame

    def is_online(self) -> bool:
        return self.status == "ONLINE"

    def reconnect(self):
        pass

    def release(self):
        self.is_running = False
        self.status = "OFFLINE"
