from typing import Optional

class FaceMetadata:
    def __init__(self, score: float, category: str, bbox: list, snapshot=None):
        self.score = score
        self.category = category
        self.bbox = bbox
        self.snapshot = snapshot

class FaceRecognizer:
    def recognize(self, face_image):
        """
        Stub for future identity matching.
        """
        raise NotImplementedError("Face recognition is not enabled in the current privacy configuration.")
