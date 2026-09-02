from collections import defaultdict

class TemporalVoter:
    def __init__(self, min_observations=3, consensus_threshold=0.60, min_confidence=0.60):
        self.min_observations = min_observations
        self.consensus_threshold = consensus_threshold
        self.min_confidence = min_confidence

    def vote(self, observations):
        """
        observations: list of tuples (plate_text, confidence)
        Returns (final_plate, final_confidence) or ("UNKNOWN", 0.0)
        """
        if len(observations) < self.min_observations:
            return "UNKNOWN", 0.0
            
        plate_scores = defaultdict(float)
        total_weight = 0.0
        
        for plate, conf in observations:
            plate_scores[plate] += conf
            total_weight += conf
            
        if not plate_scores:
            return "UNKNOWN", 0.0
            
        # Find the plate with the highest weighted score
        best_plate = max(plate_scores.items(), key=lambda x: x[1])
        
        # Calculate consensus ratio
        ratio = best_plate[1] / total_weight if total_weight > 0 else 0
        
        if ratio >= self.consensus_threshold:
            # Final confidence could be the average confidence of the winning plate
            winning_obs = [conf for p, conf in observations if p == best_plate[0]]
            avg_conf = sum(winning_obs) / len(winning_obs)
            
            if avg_conf >= self.min_confidence:
                return best_plate[0], avg_conf
            
        return "UNKNOWN", 0.0
