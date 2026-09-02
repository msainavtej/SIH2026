import argparse
import time
import yaml
import os
from camera.rtsp_camera import RTSPCamera
from camera.file_camera import FileCamera
from camera.simulated_camera import SimulatedCamera

def load_camera_config(camera_id):
    with open("configs/cameras.yaml", "r") as f:
        config = yaml.safe_load(f)
        for cam in config.get("cameras", []):
            if cam["id"] == camera_id:
                # Handle env vars
                url = cam.get("url", "")
                if url.startswith("${") and url.endswith("}"):
                    env_var = url[2:-1]
                    url = os.environ.get(env_var, "")
                cam["url"] = url
                return cam
    return None

def main():
    parser = argparse.ArgumentParser(description="Test Camera Connection")
    parser.add_argument("--camera", type=str, required=True, help="Camera ID to test")
    args = parser.parse_args()

    cam_conf = load_camera_config(args.camera)
    if not cam_conf:
        print(f"Error: Camera {args.camera} not found in configs/cameras.yaml")
        return

    print("PS187 CAMERA TEST")
    print("-" * 20)
    print(f"Camera:\n{args.camera}\n")
    source_type = cam_conf["source_type"].upper()
    print(f"Source:\n{source_type}\n")

    if source_type == "RTSP":
        cam = RTSPCamera(args.camera, cam_conf["url"])
    elif source_type == "FILE":
        cam = FileCamera(args.camera, cam_conf["url"])
    else:
        cam = SimulatedCamera(args.camera, cam_conf.get("fps", 15))

    start_time = time.time()
    cam.connect()
    time.sleep(1.0) # Wait for initial connection

    if cam.is_online():
        print("Connection:\nPASS\n")
        
        # Read a few frames to get resolution
        frames_read = 0
        h, w = 0, 0
        read_start = time.time()
        
        while frames_read < 10 and (time.time() - read_start) < 2.0:
            ret, frame = cam.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                frames_read += 1
            time.sleep(0.05)
            
        print(f"Resolution:\n{w}x{h}\n")
        print(f"FPS:\n{cam.fps}\n")
        print(f"Frames received:\n{frames_read}\n")
        
        health = cam.get_health()
        print(f"Status:\n{health['status']}\n")
    else:
        print("Connection:\nFAIL\n")
        print(f"Error:\n{cam.get_health()['last_error']}\n")

    cam.release()

if __name__ == "__main__":
    main()
