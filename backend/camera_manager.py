import cv2
import threading
import time
import yaml
import os
from typing import Dict, Any, Optional

from camera.rtsp_camera import RTSPCamera
from camera.file_camera import FileCamera
from camera.simulated_camera import SimulatedCamera
from ai.inference.pipeline import InferencePipeline

import requests
from intelligence.risk import RiskEngine
from intelligence.event_engine import EventEngine
from intelligence.correlation import SpatialTemporalCorrelationEngine, CorrelatedTrackLink
from backend.api.events_store import events_db
from backend.schemas.events import EventSchema

class CameraManager:
    def __init__(self, config_path="configs/cameras.yaml", adjacency_path="configs/adjacency.yaml"):
        self.cameras = {}
        self.pipelines = {}
        self.event_engines = {}
        self.threads = {}
        self.active_tracks: Dict[str, Dict[str, Any]] = {}
        self.correlated_links: Dict[str, CorrelatedTrackLink] = {}
        self.is_running = False
        self.config_path = config_path
        self.adjacency_path = adjacency_path
        self.correlation_engine = SpatialTemporalCorrelationEngine(config_path=adjacency_path)
        self._lock = threading.RLock()

    def load_cameras(self):
        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
            
        risk_engine = RiskEngine()
        from intelligence.zones import ZoneManager
            
        for cam_conf in config.get("cameras", []):
            if not cam_conf.get("enabled", True):
                continue
                
            cid = cam_conf["id"]
            stype = cam_conf.get("source_type", "simulated").lower()
            url = cam_conf.get("url", "")
            
            # Resolve env vars
            if url.startswith("${") and url.endswith("}"):
                url = os.environ.get(url[2:-1], "")
                
            if stype == "rtsp":
                cam = RTSPCamera(cid, url)
            elif stype == "file":
                cam = FileCamera(cid, url, loop=True)
            else:
                cam = SimulatedCamera(cid, fps=cam_conf.get("fps", 15))
                
            self.cameras[cid] = cam
            zm = ZoneManager()
            zm.load_from_yaml("configs/zones.yaml")
            self.pipelines[cid] = InferencePipeline(cam, zone_manager=zm)
            self.event_engines[cid] = EventEngine(risk_engine, correlation_engine=self.correlation_engine)
            self.active_tracks[cid] = {}

    def add_camera(self, cid: str, stype: str, url: str, fps: int = 15):
        if cid in self.cameras:
            self.pipelines[cid].stop()
            if self.threads.get(cid):
                self.threads[cid].join(timeout=1.0)
                
        risk_engine = RiskEngine()
        from intelligence.zones import ZoneManager
        zone_manager = ZoneManager()
        zone_manager.load_from_yaml("configs/zones.yaml")
        
        if stype == "rtsp":
            cam = RTSPCamera(cid, url)
        elif stype == "file":
            cam = FileCamera(cid, url, loop=True)
        else:
            cam = SimulatedCamera(cid, fps=fps)
            
        zm = ZoneManager()
        zm.load_from_yaml("configs/zones.yaml")
            
        self.cameras[cid] = cam
        self.pipelines[cid] = InferencePipeline(cam, zone_manager=zm)
        self.event_engines[cid] = EventEngine(risk_engine, correlation_engine=self.correlation_engine)
        self.active_tracks[cid] = {}
        
        if self.is_running:
            t = threading.Thread(target=self._run_pipeline, args=(cid,), daemon=True)
            self.threads[cid] = t
            t.start()

    def start_all(self):
        self.is_running = True
        for cid, cam in self.cameras.items():
            t = threading.Thread(target=self._run_pipeline, args=(cid,), daemon=True)
            self.threads[cid] = t
            t.start()

    def _enrich_and_update_events(self, link: CorrelatedTrackLink):
        """Enriches existing stored events matching source or target track IDs with correlation metadata."""
        for ev in events_db.get_all():
            updated = False
            if ev.track_id == link.source_track_id:
                ev.incident_id = link.incident_id
                ev.correlation_confidence = link.confidence_band
                ev.correlated_with_track = link.target_track_id
                ev.correlated_with_camera = link.target_camera_id
                ev.transit_time_seconds = link.transit_duration_seconds
                updated = True
            elif ev.track_id == link.target_track_id:
                ev.incident_id = link.incident_id
                ev.correlation_confidence = link.confidence_band
                ev.correlated_with_track = link.source_track_id
                ev.correlated_with_camera = link.source_camera_id
                ev.transit_time_seconds = link.transit_duration_seconds
                updated = True
            if updated:
                events_db.append(ev)

    def remove_camera(self, cid: str):
        if cid in self.cameras:
            self.pipelines[cid].is_running = False
            self.pipelines[cid].stop()
            if cid in self.threads:
                # Wait briefly then abandon if hung
                self.threads[cid].join(timeout=1.0)
                del self.threads[cid]
            del self.pipelines[cid]
            del self.event_engines[cid]
            del self.cameras[cid]
            if cid in self.active_tracks:
                del self.active_tracks[cid]

    def _run_pipeline(self, cid):
        pipeline = self.pipelines[cid]
        event_engine = self.event_engines[cid]
        pipeline.is_running = True
        
        # Connect in the background to prevent blocking FastAPI startup
        pipeline.camera.connect()
        
        while self.is_running and pipeline.is_running:
            if getattr(pipeline, 'is_paused', False):
                pipeline.camera.status = "PAUSED"
                time.sleep(0.1)
                continue
            if not pipeline.camera.is_online():
                pipeline.camera.reconnect()
                # Don't sleep/continue here, allow inference pipeline to run on last frame
                
            frame, tracks, status = pipeline.process_next_frame()
            
            if status == "OFFLINE_QUEUED":
                pipeline.camera.status = "OFFLINE - QUEUED"
            elif status == "OK":
                pipeline.camera.status = "ONLINE"
                
            if status in ["OK", "OFFLINE_QUEUED"]:
                if tracks is None:
                    tracks = []

                t_now = time.time()

                # Isolate track IDs by prepending camera_id
                for t in tracks:
                    if not str(t['track_id']).startswith(f"{cid}-"):
                        t['track_id'] = f"{cid}-{t['track_id']}"
                    t['camera_id'] = cid

                current_tracks_by_id = {str(t['track_id']): t for t in tracks}
                current_tids = set(current_tracks_by_id.keys())

                with self._lock:
                    prev_tracks_by_id = self.active_tracks.get(cid, {})
                    prev_tids = set(prev_tracks_by_id.keys())

                    new_tids = current_tids - prev_tids
                    exited_tids = prev_tids - current_tids

                    # 1. Route track exits to correlation engine
                    for tid in exited_tids:
                        last_track = prev_tracks_by_id[tid]
                        self.correlation_engine.on_track_exit(cid, last_track, timestamp=t_now)

                    # 2. Route new track entries to correlation engine
                    for tid in new_tids:
                        track = current_tracks_by_id[tid]
                        link = self.correlation_engine.on_track_entry(cid, track, timestamp=t_now)
                        if link is not None:
                            self.correlated_links[link.target_track_id] = link
                            self.correlated_links[link.source_track_id] = link
                            self._enrich_and_update_events(link)

                    self.active_tracks[cid] = current_tracks_by_id

                # 3. Process tracks through EventEngine
                events = event_engine.process_tracks(cid, frame, tracks, is_night=False, timestamp=t_now)
                for e in events:
                    with self._lock:
                        if e.track_id in self.correlated_links:
                            link = self.correlated_links[e.track_id]
                            e.incident_id = link.incident_id
                            e.correlation_confidence = link.confidence_band
                            if e.track_id == link.target_track_id:
                                e.correlated_with_track = link.source_track_id
                                e.correlated_with_camera = link.source_camera_id
                            else:
                                e.correlated_with_track = link.target_track_id
                                e.correlated_with_camera = link.target_camera_id
                            e.transit_time_seconds = link.transit_duration_seconds

                    # Append automatically updates if exists in SQLiteEventStore
                    events_db.append(e)

                # 4. Periodic cleanup of expired correlation windows
                self.correlation_engine.cleanup_expired(t_now)
                    
            if status != "OK":
                time.sleep(0.1)
                
            # Simulate real-time processing pace
            time.sleep(0.01)

    def stop_all(self):
        self.is_running = False
        for cid, pipeline in self.pipelines.items():
            pipeline.stop()
        for t in self.threads.values():
            t.join(timeout=2.0)

    def get_all_health(self):
        return [cam.get_health() for cam in self.cameras.values()]

    def get_latest_frame(self, cid):
        if cid in self.pipelines and self.pipelines[cid].current_frame is not None:
            return self.pipelines[cid].current_frame
        return None

# Global instance for FastAPI
camera_manager = CameraManager()

