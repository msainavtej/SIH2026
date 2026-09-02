import uvicorn
import threading
import time
import cv2
import yaml
import requests
from camera.camera_source import SimulatedCamera
from ai.inference.pipeline import InferencePipeline
from backend.main import app
from intelligence.zones import ZoneManager
from intelligence.risk import RiskEngine
from intelligence.event_engine import EventEngine

def run_inference_loop():
    print("Starting Inference Engine...")
    
    # Load zones
    zone_manager = ZoneManager()
    try:
        with open("configs/zones.yaml", "r") as f:
            zones_conf = yaml.safe_load(f)
            for z in zones_conf.get("zones", []):
                zone_manager.add_zone(z)
    except Exception as e:
        print(f"Could not load zones.yaml: {e}")
        
    risk_engine = RiskEngine()
    event_engine = EventEngine(risk_engine)
    
    cam = SimulatedCamera("CAM_01", fps=30)
    pipeline = InferencePipeline(cam, zone_manager=zone_manager)
    pipeline.start()
    
    try:
        while True:
            frame, tracks, status = pipeline.process_next_frame()
            if status == "OFFLINE":
                print("CAM_01 is OFFLINE. Attempting to reconnect...")
                time.sleep(1.0)
                continue
                
            if frame is not None and len(tracks) > 0:
                events = event_engine.process_tracks("CAM_01", tracks)
                for event in events:
                    if event.risk_level in ["MEDIUM", "HIGH"]:
                        print(f"ALERT: {event.risk_level} Risk: {event.reasons}")
                        # Send to backend API
                        try:
                            requests.post("http://127.0.0.1:8000/api/events", json=event.model_dump(mode='json'))
                        except Exception:
                            pass
            time.sleep(0.03) # roughly 30 fps max
    except Exception as e:
        print(f"Inference loop stopped: {e}")
    finally:
        pipeline.stop()

if __name__ == "__main__":
    # Start inference loop in background
    inference_thread = threading.Thread(target=run_inference_loop, daemon=True)
    inference_thread.start()
    
    # Start FastAPI
    print("Starting FastAPI Backend...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
