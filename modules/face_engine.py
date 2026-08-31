import cv2
import numpy as np

class FaceEngine:
    def __init__(self, match_threshold=0.80):
        self.match_threshold = match_threshold

    def evaluate_face(self, person_crop):
        """
        Extracts facial candidate matches against authorized watchlists.
        Always outputs as candidate verification only (no automatic identity confirmation).
        """
        if person_crop is None or person_crop.size == 0:
            return {"candidate_match": None, "similarity": 0.0, "status": "NO_DETECTION"}

        # Extract upper body / head region from person crop
        h, w = person_crop.shape[:2]
        head_region = person_crop[0:int(h * 0.35), 0:w]

        if head_region.size == 0:
            return {"candidate_match": None, "similarity": 0.0, "status": "NO_DETECTION"}

        # Simulated similarity score (replace with Cosine Similarity over ArcFace/FaceNet embeddings)
        simulated_similarity = 0.82

        if simulated_similarity >= self.match_threshold:
            return {
                "candidate_match": "SUSPECT_A",
                "similarity": simulated_similarity,
                "status": "OPERATOR_REVIEW_REQUIRED"
            }

        return {
            "candidate_match": None,
            "similarity": simulated_similarity,
            "status": "NO_MATCH"
        }