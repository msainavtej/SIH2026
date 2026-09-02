import cv2
import time
import threading
from camera.base import CameraSource

class RTSPCamera(CameraSource):
    def __init__(self, camera_id: str, url: str):
        super().__init__(camera_id)
        self.url = url
        self.cap = None
        self.thread = None
        self.latest_frame = None
        self.lock = threading.Lock()
        
    def connect(self):
        self.status = "CONNECTING"
        self.cap = cv2.VideoCapture(self.url)
        if self.cap.isOpened():
            self.status = "ONLINE"
            self.is_running = True
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
            self.last_error = ""
            
            # Start background reader thread to always have latest frame
            self.thread = threading.Thread(target=self._update, daemon=True)
            self.thread.start()
        else:
            self.status = "OFFLINE"
            self.last_error = "Could not connect to RTSP stream."
            self.is_running = False

    def _update(self):
        while self.is_running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
                    self.frames_received += 1
                    self.last_frame_time = time.time()
                else:
                    self.status = "DEGRADED"
                    self.last_error = "Stream interrupted."
                    time.sleep(0.1) # Prevent busy loop on disconnect
            else:
                time.sleep(0.1)

    def read(self):
        if not self.is_running or self.status in ["OFFLINE", "CONNECTING"]:
            return False, None
            
        with self.lock:
            frame = self.latest_frame.copy() if self.latest_frame is not None else None
            
        if frame is None:
            # If we've never received a frame but we're online, just wait
            if time.time() - self.last_frame_time > 5.0 and self.last_frame_time > 0:
                self.status = "DEGRADED"
            return False, None
            
        return True, frame

    def is_online(self) -> bool:
        return self.status == "ONLINE"

    def reconnect(self):
        self.status = "RECONNECTING"
        self.reconnect_count += 1
        self.release()
        time.sleep(1.0)
        self.connect()

    def release(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
        self.status = "OFFLINE"
