from collections import deque
import time

class TrajectoryManager:
    def __init__(self, max_history=30):
        self.max_history = max_history
        # Maps track_id -> dict with 'history': deque of [x,y], 'last_seen': timestamp, 'type': string
        self.tracks = {}
        
    def update(self, current_tracks):
        """
        Takes a list of tracked object dicts from the tracker.
        Updates internal trajectories.
        """
        current_time = time.time()
        active_ids = set()
        
        for track in current_tracks:
            tid = track['track_id']
            active_ids.add(tid)
            
            # Calculate center point of bbox
            x1, y1, x2, y2 = track['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            if tid not in self.tracks:
                self.tracks[tid] = {
                    'history': deque(maxlen=self.max_history),
                    'type': track['object_type'],
                    'first_seen': current_time
                }
                
            self.tracks[tid]['history'].append([center_x, center_y])
            self.tracks[tid]['last_seen'] = current_time
            
        return active_ids
            
    def cleanup(self, timeout_sec=5.0):
        """
        Remove tracks that haven't been seen for a while.
        """
        current_time = time.time()
        to_delete = []
        for tid, data in self.tracks.items():
            if current_time - data['last_seen'] > timeout_sec:
                to_delete.append(tid)
                
        for tid in to_delete:
            del self.tracks[tid]
            
    def get_trajectory(self, track_id):
        if track_id in self.tracks:
            return list(self.tracks[track_id]['history'])
        return []
