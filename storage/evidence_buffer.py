import cv2
import collections
import time
import os

class EvidenceBuffer:
    def __init__(self, pre_event_sec=5, post_event_sec=5, fps=15):
        self.pre_event_frames = pre_event_sec * fps
        self.post_event_frames = post_event_sec * fps
        self.fps = fps
        # Map camera_id -> deque of frames
        self.buffers = collections.defaultdict(lambda: collections.deque(maxlen=self.pre_event_frames))
        # Active recordings: event_id -> dict with state
        self.active_recordings = {}

    def add_frame(self, camera_id, frame):
        """
        Add a frame to the rolling buffer.
        """
        # Save a copy to prevent overwriting issues if frame is modified later
        frame_copy = frame.copy()
        self.buffers[camera_id].append(frame_copy)
        
        # Process active recordings
        completed = []
        for event_id, rec in self.active_recordings.items():
            if rec['camera_id'] == camera_id:
                if rec['frames_to_record'] > 0:
                    rec['writer'].write(frame_copy)
                    rec['frames_to_record'] -= 1
                if rec['frames_to_record'] <= 0:
                    rec['writer'].release()
                    completed.append(event_id)
                    
        for eid in completed:
            del self.active_recordings[eid]

    def trigger_event(self, event_id, camera_id, output_path):
        """
        Start recording post-event and dump pre-event buffer.
        """
        if not self.buffers[camera_id]:
            return False
            
        height, width = self.buffers[camera_id][0].shape[:2]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # We use XVID or mp4v
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
        
        # Dump pre-event buffer
        for f in self.buffers[camera_id]:
            writer.write(f)
            
        # Register for post-event
        self.active_recordings[event_id] = {
            'camera_id': camera_id,
            'writer': writer,
            'frames_to_record': self.post_event_frames
        }
        
        return True
