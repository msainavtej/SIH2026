import time
from abc import ABC, abstractmethod
from typing import Dict, Any

class CameraSource(ABC):
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.fps = 0.0
        self.is_running = False
        self.status = "OFFLINE"
        self.frames_received = 0
        self.dropped_frames = 0
        self.reconnect_count = 0
        self.last_frame_time = 0.0
        self.last_error = ""

    @abstractmethod
    def connect(self):
        """Initial connection."""
        pass

    @abstractmethod
    def read(self):
        """Read a frame. Returns (ret, frame)"""
        pass

    @abstractmethod
    def is_online(self) -> bool:
        """Check if camera is currently connected and healthy."""
        pass

    @abstractmethod
    def reconnect(self):
        """Attempt to reconnect."""
        pass

    @abstractmethod
    def release(self):
        """Release resources and stop."""
        pass

    def get_health(self) -> Dict[str, Any]:
        """Return camera health metadata."""
        return {
            "camera_id": self.camera_id,
            "status": self.status,
            "last_frame_time": self.last_frame_time,
            "fps": round(self.fps, 2) if self.fps else 0,
            "frames_received": self.frames_received,
            "dropped_frames": self.dropped_frames,
            "reconnect_count": self.reconnect_count,
            "last_error": self.last_error
        }

    # Backward compatibility with start/stop used in pipeline
    def start(self):
        self.connect()

    def stop(self):
        self.release()
