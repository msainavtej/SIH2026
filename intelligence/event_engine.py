from intelligence.risk import RiskEngine
from backend.schemas.events import EventSchema
import datetime
import uuid
import time

class EventEngine:
    def __init__(self, risk_engine: RiskEngine, correlation_engine=None):
        self.risk_engine = risk_engine
        self.correlation_engine = correlation_engine
        self.active_events = {} # Track ID -> EventSchema
        self.last_known_tracks = {} # Track ID -> Track Dict

    def process_tracks(self, camera_id, frame, tracks, is_night=False, timestamp=None):
        """
        Processes a list of enriched tracks from a single frame and generates event state changes.
        Returns ONLY events that have changed state (new, escalated, resolved).
        """
        events_emitted = []
        current_tids = set()
        t_now = float(timestamp) if timestamp is not None else time.time()
        
        for track in tracks:
            tid = track['track_id']
            current_tids.add(tid)
            self.last_known_tracks[tid] = track
            zones = track.get('zones', [])
            dwell = track.get('dwell_time', 0)
            
            # Context for risk evaluation
            context = {
                'direction': track.get('direction'),
                'dwell_time': int(dwell),
                'is_night': is_night,
                'zone': zones[0] if zones else None
            }
            
            # Trigger conditions
            is_zone_intrusion = zones and dwell > self.risk_engine.thresholds['dwell_intrusion_seconds']
            is_night_movement = is_night and track['object_type'] == 'person'
            has_plate = 'plate' in track
            
            if is_zone_intrusion or is_night_movement or has_plate:
                # Determine primary event type
                event_type = 'ZONE_INTRUSION' if is_zone_intrusion else 'NIGHT_MOVEMENT'
                if has_plate and not is_zone_intrusion and not is_night_movement:
                    event_type = 'VEHICLE_DETECTED'
                    
                # False-Positive Suppression / Wildlife logic
                animal_classes = ['bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'animal']
                if track['object_type'] in animal_classes:
                    event_type = 'WILDLIFE_ACTIVITY'
                    
                context['plate'] = track.get('plate')
                score, level, reasons, breakdown = self.risk_engine.evaluate(event_type, context)
                
                if tid not in self.active_events:
                    # NEW EVENT (Candidate -> Active)
                    from backend.storage_manager import storage_manager
                    
                    eid = f"EVT-{datetime.datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
                    ev_path = storage_manager.save_snapshot(eid, frame)
                    
                    event = EventSchema(
                        event_id=eid,
                        camera_id=camera_id,
                        timestamp=datetime.datetime.utcnow(),
                        start_time=datetime.datetime.utcnow(),
                        status="ACTIVE",
                        track_id=tid,
                        object_type=track['object_type'],
                        confidence=track['confidence'],
                        plate=track.get('plate'),
                        plate_confidence=track.get('plate_confidence'),
                        plate_observations=track.get('plate_observations'),
                        has_face=track.get('has_face', False),
                        face_score=track.get('face_score'),
                        face_category=track.get('face_category'),
                        zone=zones[0] if zones else None,
                        direction=track.get('direction'),
                        dwell_seconds=int(dwell),
                        risk_score=score,
                        max_risk_score=score,
                        risk_level=level,
                        reasons=reasons,
                        score_breakdown=breakdown,
                        evidence_path=ev_path
                    )
                    self.active_events[tid] = event
                    events_emitted.append(event)
                else:
                    # EXISTING EVENT
                    event = self.active_events[tid]
                    changed = False
                    
                    # Update plate if it wasn't there before
                    if track.get('plate') and not event.plate:
                        event.plate = track.get('plate')
                        event.plate_confidence = track.get('plate_confidence')
                        event.plate_observations = track.get('plate_observations')
                        changed = True
                        
                    # Update face if it wasn't there before
                    if track.get('has_face') and not event.has_face:
                        event.has_face = True
                        event.face_score = track.get('face_score')
                        event.face_category = track.get('face_category')
                        changed = True
                    
                    if score > event.max_risk_score:
                        event.max_risk_score = score
                        event.risk_score = score
                        event.risk_level = level
                        event.reasons = reasons
                        event.score_breakdown = breakdown
                        changed = True
                        
                    event.dwell_seconds = int(dwell)
                    event.direction = track.get('direction')
                    
                    if changed:
                        events_emitted.append(event)
            else:
                # Track is no longer in a restricted zone (or didn't meet dwell).
                # If it had an active event, we resolve it.
                if tid in self.active_events:
                    event = self.active_events.pop(tid)
                    event.status = "RESOLVED"
                    event.end_time = datetime.datetime.utcnow()
                    events_emitted.append(event)
                    
        # Check for tracks that disappeared completely
        lost_tids = list(set(self.active_events.keys()) - current_tids)
        for tid in lost_tids:
            event = self.active_events.pop(tid)
            event.status = "RESOLVED"
            event.end_time = datetime.datetime.utcnow()
            events_emitted.append(event)
            
            # Hook track exit event into correlation engine if configured
            if self.correlation_engine is not None and tid in self.last_known_tracks:
                self.correlation_engine.on_track_exit(camera_id, self.last_known_tracks[tid], timestamp=t_now)

        # Purge stale last known tracks
        for tid in list(self.last_known_tracks.keys()):
            if tid not in current_tids and tid not in self.active_events:
                self.last_known_tracks.pop(tid, None)
            
        return events_emitted
