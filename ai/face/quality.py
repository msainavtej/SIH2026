import cv2
import numpy as np

class FaceQualityFilter:
    def __init__(self, min_width=30):
        self.min_width = min_width

    def assess_quality(self, face_crop, detection_conf):
        """
        Assess face quality (0-100). Returns (score, category).
        """
        if face_crop is None or face_crop.size == 0:
            return 0, "UNUSABLE"
            
        h, w = face_crop.shape[:2]
        
        # 1. Size score (0-30 points)
        # Optimal size > 100px. Minimum is self.min_width.
        if w < self.min_width:
            return 0, "UNUSABLE"
            
        size_score = min(30, (w - self.min_width) / max(1, 100 - self.min_width) * 30)
            
        # 2. Sharpness score (0-40 points)
        # Variance of Laplacian. Threshold usually around 100 for "sharp".
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharp_score = min(40, (sharpness / 150.0) * 40)
        
        # 3. Brightness/Contrast score (0-10 points)
        # Avoid too dark (< 30 mean) or too bright (> 220 mean)
        mean_val = np.mean(gray)
        if mean_val < 30 or mean_val > 220:
            bright_score = 0
        else:
            bright_score = 10
            
        # 4. Confidence (0-20 points)
        conf_score = min(20, detection_conf * 20)
        
        total_score = int(size_score + sharp_score + bright_score + conf_score)
        
        # Determine category
        if total_score >= 80:
            category = "HIGH"
        elif total_score >= 60:
            category = "MEDIUM"
        elif total_score >= 40:
            category = "LOW"
        else:
            category = "UNUSABLE"
            
        return total_score, category
