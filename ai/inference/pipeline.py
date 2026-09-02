import cv2
import time
from camera.base import CameraSource
from ai.tracking.tracker import ByteTracker
from ai.tracking.trajectory import TrajectoryManager
from intelligence.zones import ZoneManager
from intelligence.direction import DirectionEstimator
from intelligence.loitering import DwellTracker
from backend.schemas.events import TrackedObject
from ai.anpr.pipeline import ANPRPipeline
from ai.face.pipeline import FacePipeline

class InferencePipeline:
    def __init__(self, camera: CameraSource, zone_manager: ZoneManager = None):
        self.camera = camera
        self.tracker = ByteTracker(model_path="yolov8n.pt")
        self.trajectory_manager = TrajectoryManager(max_history=30)
        self.direction_estimator = DirectionEstimator(history_frames=15)
        self.dwell_tracker = DwellTracker()
        self.anpr = ANPRPipeline()
        self.face = FacePipeline()
        
        # Default to an empty zone manager if none provided
        self.zone_manager = zone_manager if zone_manager else ZoneManager()
        
        self.is_running = False
        self.current_frame = None
        self.current_tracks = []
        
    def start(self):
        self.camera.start()
        self.is_running = True
        
    def stop(self):
        self.is_running = False
        self.camera.stop()
        
    def process_next_frame(self):
        if not self.is_running:
            return None, [], "STOPPED"
            
        try:
            ret, frame = self.camera.read()
        except Exception as e:
            ret = False
            frame = None
            
        if not ret or frame is None:
            if self.current_frame is not None:
                # Reuse last frame for offline queueing
                frame = self.current_frame
                status = "OFFLINE_QUEUED"
            else:
                return None, [], "OFFLINE"
        else:
            status = "OK"
            
        self.current_frame = frame.copy()
        
        # Run tracking
        start_time = time.time()
        raw_tracks = self.tracker.track(self.current_frame)
        
        # Update trajectories
        active_ids = self.trajectory_manager.update(raw_tracks)
        self.trajectory_manager.cleanup()
        self.dwell_tracker.cleanup(active_ids)
        self.anpr.cleanup(active_ids)
        self.face.cleanup(active_ids)
        
        enriched_tracks = []
        current_time = time.time()
        
        # Contextual Enrichment
        for track in raw_tracks:
            tid = track['track_id']
            x1, y1, x2, y2 = track['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            point = [center_x, center_y]
            
            # Selective ANPR
            if track['object_type'] in self.anpr.vehicle_classes and track['confidence'] >= self.anpr.min_vehicle_conf:
                vehicle_crop = self.current_frame 
                mock_inject = track.get('_mock_ocr') 
                plate, p_conf, obs = self.anpr.process_vehicle(tid, vehicle_crop, current_time, mock_inject)
                if plate:
                    track['plate'] = plate
                    track['plate_confidence'] = p_conf
                    track['plate_observations'] = obs
            
            # 1. Zones
            zones_in = self.zone_manager.check_point_in_zones(point)
            track['zones'] = zones_in
            
            # Selective Face
            is_relevant_event = len(zones_in) > 0 or track.get('_force_face_trigger', False)
            if track['object_type'] == 'person' and is_relevant_event:
                person_crop = self.current_frame
                mock_inject = track.get('_mock_face')
                face_meta = self.face.process_person(tid, person_crop, current_time, mock_inject)
                if face_meta:
                    track['has_face'] = True
                    track['face_score'] = face_meta.score
                    track['face_category'] = face_meta.category
            
            # 2. Direction
            traj = self.trajectory_manager.get_trajectory(tid)
            direction = self.direction_estimator.estimate(traj)
            track['direction'] = direction
            
            # 3. Loitering/Dwell
            in_restricted = any(self.zone_manager.zones[z].zone_type == 'restricted' for z in zones_in)
            dwell_time = self.dwell_tracker.update_dwell(tid, in_restricted)
            track['dwell_time'] = dwell_time
            
            enriched_tracks.append(track)
            
            # Visualization
            color = (0, 0, 255) if in_restricted else (0, 255, 0)
            cv2.rectangle(self.current_frame, (x1, y1), (x2, y2), color, 2)
            
            label = f"{tid} {track['object_type']}"
            if direction:
                label += f" [{direction}]"
            if dwell_time > 0:
                label += f" D:{int(dwell_time)}s"
                
            cv2.putText(self.current_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw trajectory tail
            if len(traj) > 1:
                for i in range(1, len(traj)):
                    cv2.line(self.current_frame, tuple(traj[i-1]), tuple(traj[i]), (255, 0, 0), 2)
            
        # Draw Zones
        for z_id, zone in self.zone_manager.zones.items():
            color = (0, 0, 255) if zone.zone_type == 'restricted' else (255, 0, 0)
            pts = zone.polygon
            cv2.polylines(self.current_frame, [pts], isClosed=True, color=color, thickness=2)
            # Zone label
            cv2.putText(self.current_frame, z_id, tuple(pts[0][0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        latency = time.time() - start_time
        fps_text = f"Latency: {latency*1000:.1f}ms | Zones: {len(self.zone_manager.zones)}"
        cv2.putText(self.current_frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        self.current_tracks = enriched_tracks
        return self.current_frame, self.current_tracks, status
