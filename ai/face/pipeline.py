import time
import yaml
import os
import cv2
import numpy as np
from ai.face.detector import MockFaceDetector
from ai.face.quality import FaceQualityFilter
from ai.face.models import FaceMetadata

class FaceTrackState:
    def __init__(self, track_id):
        self.track_id = track_id
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.frames_sampled = 0
        self.best_face_score = -1
        self.best_metadata = None
        self.completed = False

class FacePipeline:
    def __init__(self, config_path="configs/face.yaml"):
        self.enabled = False
        self.relevant_events = ['ZONE_INTRUSION', 'BORDER_APPROACH', 'HIGH_RISK']
        self.max_frames = 5
        self.interval_sec = 0.150
        
        self.detector = MockFaceDetector()
        self.quality = FaceQualityFilter()
        self.track_states = {}
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                conf = yaml.safe_load(f)
                if conf and conf.get("face", {}).get("enabled", False):
                    self.enabled = True
                    fconf = conf["face"]
                    self.relevant_events = fconf.get("trigger", {}).get("relevant_events", self.relevant_events)
                    self.max_frames = fconf.get("sampling", {}).get("max_frames_per_track", 5)
                    self.interval_sec = fconf.get("sampling", {}).get("interval_ms", 150) / 1000.0
                    
                    q = fconf.get("quality", {})
                    self.quality = FaceQualityFilter(min_width=q.get("min_face_width", 30))

    def _generate_synthetic_crop(self, w, h, sharpness_mock, brightness_mock=128):
        """Generates a dummy numpy array to pass into quality filter for testing"""
        # Create grey square
        img = np.ones((h, w, 3), dtype=np.uint8) * brightness_mock
        # Add noise to simulate sharpness (variance of laplacian)
        noise = np.random.normal(0, sharpness_mock, (h, w, 3)).astype(np.uint8)
        return cv2.add(img, noise)

    def process_person(self, track_id, person_crop, current_time, mock_face_inject=None):
        """
        Samples face frames for a person track.
        Returns FaceMetadata if completed, else None.
        """
        if not self.enabled:
            return None
            
        if track_id not in self.track_states:
            self.track_states[track_id] = FaceTrackState(track_id)
            
        state = self.track_states[track_id]
        
        if state.completed:
            return state.best_metadata
            
        if state.frames_sampled > 0 and (current_time - state.last_seen) < self.interval_sec:
            return None
            
        # Run detection
        try:
            if mock_face_inject is not None:
                # mock_face_inject is e.g. ([0,0,50,50], 0.9, sharpness_modifier, [brightness])
                bbox = mock_face_inject[0]
                conf = mock_face_inject[1]
                sharpness = mock_face_inject[2]
                brightness = mock_face_inject[3] if len(mock_face_inject) > 3 else 128
                
                self.detector.mock_return = bbox
                self.detector.mock_conf = conf
                
                faces = self.detector.detect(person_crop)
                for f_bbox, f_conf in faces:
                    w = f_bbox[2] - f_bbox[0]
                    h = f_bbox[3] - f_bbox[1]
                    mock_crop = self._generate_synthetic_crop(w, h, sharpness, brightness)
                    score, category = self.quality.assess_quality(mock_crop, f_conf)
                    
                    if score > state.best_face_score:
                        state.best_face_score = score
                        state.best_metadata = FaceMetadata(score, category, f_bbox, None)
                        
        except Exception as e:
            print(f"FACE AI ERROR on track {track_id}: {e}")
            
        state.last_seen = current_time
        state.frames_sampled += 1
        
        if state.frames_sampled >= self.max_frames:
            state.completed = True
            return state.best_metadata
            
        return None
        
    def cleanup(self, active_track_ids):
        to_del = [tid for tid in self.track_states if tid not in active_track_ids]
        for tid in to_del:
            del self.track_states[tid]
