class FaceDetector:
    def detect(self, frame):
        """
        Abstract face detection. Returns list of (bbox, confidence).
        """
        raise NotImplementedError

class MockFaceDetector(FaceDetector):
    def __init__(self):
        self.mock_return = None
        self.mock_conf = 0.0
        
    def detect(self, person_crop):
        """
        Mock detector for simulator.
        Returns one face if injected.
        """
        if self.mock_return:
            # mock_return is a bounding box e.g. [0, 0, 50, 50]
            return [(self.mock_return, self.mock_conf)]
        return []
