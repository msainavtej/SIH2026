import time
import yaml
import os
from ai.anpr.plate_detector import PlateDetector
from ai.anpr.quality import QualityFilter
from ai.anpr.ocr import MockOCREngine
from ai.anpr.voting import TemporalVoter

class ANPRTrackState:
    def __init__(self, track_id):
        self.track_id = track_id
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.frames_sampled = 0
        self.observations = [] # list of (plate, conf)
        self.final_plate = None
        self.final_confidence = 0.0
        self.completed = False

class ANPRPipeline:
    def __init__(self, config_path="configs/anpr.yaml"):
        self.enabled = False
        self.vehicle_classes = ['car', 'truck', 'bus', 'motorcycle']
        self.min_vehicle_conf = 0.50
        self.max_frames = 5
        self.interval_sec = 0.150
        
        self.detector = PlateDetector()
        self.quality = QualityFilter()
        self.ocr = MockOCREngine()
        self.voter = TemporalVoter()
        self.track_states = {}
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                conf = yaml.safe_load(f)
                if conf and conf.get("anpr", {}).get("enabled", False):
                    self.enabled = True
                    anpr_conf = conf["anpr"]
                    self.vehicle_classes = anpr_conf.get("trigger", {}).get("vehicle_classes", self.vehicle_classes)
                    self.max_frames = anpr_conf.get("sampling", {}).get("max_frames_per_track", 5)
                    self.interval_sec = anpr_conf.get("sampling", {}).get("interval_ms", 150) / 1000.0
                    
                    q = anpr_conf.get("quality", {})
                    self.quality = QualityFilter(q.get("min_plate_width", 40), q.get("min_sharpness", 50))
                    
                    v = anpr_conf.get("voting", {})
                    self.voter = TemporalVoter(v.get("min_observations", 3), v.get("consensus_threshold", 0.6), anpr_conf.get("ocr", {}).get("min_confidence", 0.6))

    def process_vehicle(self, track_id, vehicle_crop, current_time, mock_ocr_inject=None):
        """
        Processes a vehicle crop if it meets triggering and sampling conditions.
        Returns (plate, conf, obs_count) if completed, else (None, 0, 0).
        """
        if not self.enabled:
            return None, 0.0, 0
            
        if track_id not in self.track_states:
            self.track_states[track_id] = ANPRTrackState(track_id)
            
        state = self.track_states[track_id]
        
        if state.completed:
            return state.final_plate, state.final_confidence, len(state.observations)
            
        # Enforce sampling interval
        if len(state.observations) > 0 and (current_time - state.last_seen) < self.interval_sec:
            return None, 0.0, len(state.observations)
            
        # Run detection
        try:
            is_good = True
            if vehicle_crop is not None:
                plate_crop, det_conf = self.detector.detect(vehicle_crop)
                is_good, reason = self.quality.check_quality(plate_crop)
            else:
                plate_crop = None
            
            if is_good:
                if mock_ocr_inject is not None:
                    self.ocr.mock_return, self.ocr.mock_confidence = mock_ocr_inject
                else:
                    self.ocr.mock_return, self.ocr.mock_confidence = None, 0.0
                    
                plate, ocr_conf = self.ocr.read_plate(plate_crop)
                if plate:
                    state.observations.append((plate, ocr_conf))
                    
        except Exception as e:
            # Failure Isolation
            print(f"ANPR ERROR on track {track_id}: {e}")
            
        state.last_seen = current_time
        
        state.frames_sampled += 1
        
        # Check if we should finalize
        if state.frames_sampled >= self.max_frames:
            state.completed = True
            state.final_plate, state.final_confidence = self.voter.vote(state.observations)
            return state.final_plate, state.final_confidence, len(state.observations)
            
        return None, 0.0, len(state.observations)
        
    def cleanup(self, active_track_ids):
        to_del = [tid for tid in self.track_states if tid not in active_track_ids]
        for tid in to_del:
            del self.track_states[tid]
