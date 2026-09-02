import argparse
import time
from camera.camera_source import SimulatedCamera

def run_simulator(duration: int = 10):
    print("Starting Border Surveillance Simulator...")
    cam1 = SimulatedCamera("CAM_BORDER_01", fps=15)
    cam1.start()
    
    print(f"Simulator running for {duration} seconds.")
    start_time = time.time()
    frames_read = 0
    
    while time.time() - start_time < duration:
        ret, frame = cam1.read()
        if ret:
            frames_read += 1
            if frames_read % 15 == 0:
                print(f"[{time.strftime('%H:%M:%S')}] Heartbeat: CAM_BORDER_01 generated 15 frames.")
    
    cam1.stop()
    print(f"Simulator stopped. Total frames: {frames_read}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Border AI Simulator")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds")
    args = parser.parse_args()
    run_simulator(args.duration)
