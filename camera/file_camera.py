import cv2
import time
from camera.base import CameraSource

class FileCamera(CameraSource):
    def __init__(self, camera_id: str, filepath: str, loop: bool = True):
        super().__init__(camera_id)
        self.filepath = filepath
        self.loop = loop
        self.cap = None

    def connect(self):
        self.status = "CONNECTING"
        self.cap = cv2.VideoCapture(self.filepath)
        if self.cap.isOpened():
            self.status = "ONLINE"
            self.is_running = True
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.last_error = ""
        else:
            self.status = "OFFLINE"
            self.last_error = "Could not open file."
            self.is_running = False

    def read(self):
        if not self.is_running or not self.cap:
            return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            else:
                self.status = "OFFLINE"
                self.is_running = False
                
        if ret:
            self.frames_received += 1
            self.last_frame_time = time.time()
            
        return ret, frame

    def is_online(self) -> bool:
        return self.status == "ONLINE"

    def reconnect(self):
        self.reconnect_count += 1
        self.release()
        self.connect()

    def release(self):
        self.is_running = False
        self.status = "OFFLINE"
        if self.cap:
            self.cap.release()
            self.cap = None
