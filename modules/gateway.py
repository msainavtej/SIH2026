import cv2

class StreamGateway:
    def __init__(self, source):
        self.source = source
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.source)
        return self.cap.isOpened()

    def get_frames(self):
        while self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame

    def release(self):
        if self.cap:
            self.cap.release()
