import math

def calculate_direction(p1, p2):
    """
    Calculate compass direction from point p1 to p2.
    Returns string: N, NE, E, SE, S, SW, W, NW or None if no movement.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]  # Note: y-axis is inverted in image coordinates (top is 0)
    
    # If movement is very small, we might consider it 'stationary' or None
    if abs(dx) < 5 and abs(dy) < 5:
        return None
        
    # Standard math.atan2(y, x) -> but our Y is inverted!
    # So we use -dy to make standard cartesian angle where Up is positive Y
    angle_rad = math.atan2(-dy, dx)
    angle_deg = math.degrees(angle_rad)
    if angle_deg < 0:
        angle_deg += 360
        
    # Map to compass directions (45 degree slices, offset by 22.5)
    directions = ["E", "NE", "N", "NW", "W", "SW", "S", "SE", "E"]
    idx = int((angle_deg + 22.5) // 45)
    return directions[idx]

class DirectionEstimator:
    def __init__(self, history_frames=15):
        self.history_frames = history_frames
        
    def estimate(self, trajectory):
        """
        Takes a list of [x,y] points representing trajectory history.
        Estimates the general direction.
        """
        if len(trajectory) < 2:
            return None
            
        # Compare current point with a point 'history_frames' ago, or the oldest point
        start_idx = max(0, len(trajectory) - self.history_frames)
        start_point = trajectory[start_idx]
        end_point = trajectory[-1]
        
        return calculate_direction(start_point, end_point)
