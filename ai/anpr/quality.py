import cv2

class QualityFilter:
    def __init__(self, min_width=40, min_sharpness=50):
        self.min_width = min_width
        self.min_sharpness = min_sharpness

    def check_quality(self, plate_crop):
        """
        Check if the plate crop meets quality standards for OCR.
        Returns (is_good, reason)
        """
        if plate_crop is None or plate_crop.size == 0:
            return False, "Empty crop"

        h, w = plate_crop.shape[:2]
        if w < self.min_width:
            return False, "Too small"

        # Calculate sharpness using variance of Laplacian
        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if len(plate_crop.shape) == 3 else plate_crop
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if sharpness < self.min_sharpness:
            return False, f"Blurry ({sharpness:.1f})"

        return True, "Good"
