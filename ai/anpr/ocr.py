import re

class OCREngine:
    def read_plate(self, plate_crop):
        raise NotImplementedError

class MockOCREngine(OCREngine):
    def __init__(self):
        # We can inject mock returns for testing simulator scenarios
        self.mock_return = None
        self.mock_confidence = 0.9

    def read_plate(self, plate_crop):
        # Return mocked plate and confidence
        if self.mock_return:
            return self.normalize(self.mock_return), self.mock_confidence
        return None, 0.0

    def normalize(self, text):
        """
        Safe normalization for Indian plates.
        - Uppercase
        - Remove whitespaces/dashes
        """
        if not text:
            return ""
        text = text.upper()
        text = re.sub(r'[^A-Z0-9]', '', text)
        return text
