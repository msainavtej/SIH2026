import time

class DwellTracker:
    def __init__(self):
        # Dictionary mapping track_id -> dict with 'first_seen' and 'last_seen' in a zone
        self.dwell_states = {}
        
    def update_dwell(self, track_id, in_zone):
        """
        Updates dwell time for a track.
        in_zone: boolean, whether the object is currently in a restricted/monitored zone.
        Returns the current dwell time in seconds (0 if not in zone).
        """
        current_time = time.time()
        
        if in_zone:
            if track_id not in self.dwell_states:
                self.dwell_states[track_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time
                }
                return 0
            else:
                self.dwell_states[track_id]['last_seen'] = current_time
                return current_time - self.dwell_states[track_id]['first_seen']
        else:
            # If not in zone, we can optionally clear the state or keep it for a grace period
            if track_id in self.dwell_states:
                # If they leave the zone, we might want a grace period before resetting.
                # For simplicity, if they are not in the zone, dwell is 0. 
                # (Grace period cleanup should be handled in a cleanup method).
                pass
            return 0
            
    def cleanup(self, active_track_ids, grace_period_sec=5.0):
        """
        Remove track IDs that are no longer active to prevent memory leaks.
        """
        current_time = time.time()
        keys_to_remove = []
        for tid, state in self.dwell_states.items():
            if tid not in active_track_ids:
                if (current_time - state['last_seen']) > grace_period_sec:
                    keys_to_remove.append(tid)
                    
        for k in keys_to_remove:
            del self.dwell_states[k]
