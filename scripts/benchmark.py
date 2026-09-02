import time
import os
import cv2
import numpy as np
from camera.simulated_camera import SimulatedCamera
from ai.inference.pipeline import InferencePipeline
import threading

def run_pipeline(pipeline, end_time, counts, idx):
    frames = 0
    while time.time() < end_time:
        ret, frame = pipeline.camera.read()
        if not ret:
            time.sleep(0.01)
            continue
        pipeline.current_frame = frame
        f, t, s = pipeline.process_next_frame()
        frames += 1
    counts[idx] = frames

def run_benchmark(duration_seconds=10, num_cameras=1):
    print(f"Starting performance benchmark for {duration_seconds} seconds with {num_cameras} cameras...")
    
    pipelines = []
    for i in range(num_cameras):
        cam = SimulatedCamera(f"CAM{i}", fps=15)
        cam.connect()
        pipeline = InferencePipeline(cam)
        pipeline.is_running = True
        pipelines.append(pipeline)
        
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    counts = [0] * num_cameras
    threads = []
    
    for i in range(num_cameras):
        t = threading.Thread(target=run_pipeline, args=(pipelines[i], end_time, counts, i))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    total_frames = sum(counts)
    actual_duration = time.time() - start_time
    fps = total_frames / actual_duration
    
    print("\nBenchmark complete!")
    print(f"Total Frames Processed: {total_frames}")
    print(f"Effective Total FPS: {fps:.2f}")
    
    return fps

if __name__ == "__main__":
    fps_1 = run_benchmark(5, 1)
    fps_2 = run_benchmark(5, 2)
    fps_4 = run_benchmark(5, 4)
    
    with open("docs/performance.md", "a") as f:
        f.write("\n### Multi-Camera Scalability\n")
        f.write(f"- **1 Camera:** ~{fps_1:.2f} Total FPS\n")
        f.write(f"- **2 Cameras:** ~{fps_2:.2f} Total FPS\n")
        f.write(f"- **4 Cameras:** ~{fps_4:.2f} Total FPS\n")
