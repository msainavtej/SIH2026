import time
import requests
import datetime
from intelligence.zones import ZoneManager
from intelligence.risk import RiskEngine
from intelligence.event_engine import EventEngine

def run_scenario(scenario_name, tracks_sequence):
    print(f"\n--- Running Scenario: {scenario_name} ---")
    
    zone_manager = ZoneManager()
    zone_manager.add_zone({
        "id": "RED-03",
        "type": "restricted",
        "polygon": [[100, 100], [500, 100], [500, 400], [100, 400]],
        "border_direction": "NE"
    })
    
    risk_engine = RiskEngine()
    event_engine = EventEngine(risk_engine)
    
    for i, tracks in enumerate(tracks_sequence):
        print(f"Step {i+1}: {len(tracks)} objects detected.")
        events = event_engine.process_tracks("CAM_SIM", tracks)
        for evt in events:
            print(f"  -> ALERT: {evt.risk_level} Risk ({evt.risk_score})")
            print(f"  -> Reasons: {evt.reasons}")
            try:
                requests.post("http://127.0.0.1:8000/api/events", json=evt.model_dump(mode='json'))
            except Exception:
                pass
        time.sleep(1)
        
# Scenario A: Normal vehicle (No Alert)
seq_a = [
    [{"track_id": "V1", "object_type": "car", "confidence": 0.9, "bbox": [50, 50, 90, 90], "zones": [], "dwell_time": 0, "direction": "E"}],
    [{"track_id": "V1", "object_type": "car", "confidence": 0.9, "bbox": [60, 50, 100, 90], "zones": [], "dwell_time": 1, "direction": "E"}],
]

# Scenario C: Night Intrusion + Border Approach
seq_c = [
    [{"track_id": "P1", "object_type": "person", "confidence": 0.85, "bbox": [200, 200, 250, 300], "zones": ["RED-03"], "dwell_time": 1, "direction": "N"}],
    [{"track_id": "P1", "object_type": "person", "confidence": 0.85, "bbox": [210, 180, 260, 280], "zones": ["RED-03"], "dwell_time": 3, "direction": "NE"}], # Dwell > 2s triggers event
    [{"track_id": "P1", "object_type": "person", "confidence": 0.85, "bbox": [220, 160, 270, 260], "zones": ["RED-03"], "dwell_time": 32, "direction": "NE"}], # Loitering
]

if __name__ == "__main__":
    run_scenario("Normal Vehicle", seq_a)
    run_scenario("Night Intrusion", seq_c)
