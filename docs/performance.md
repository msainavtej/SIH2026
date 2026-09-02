# Performance Benchmark Report

### Selective AI Pipeline (ANPR & Face) vs Baseline

Selective AI ensures we only run heavy models (plate detection, face detection) on specific tracks triggering relevant events, preventing unnecessary compute on empty frames or innocent pedestrians.

- **Baseline Tracking FPS:** ~9.90 FPS
- **Selective Face & ANPR FPS:** ~8.37 FPS
- **Average End-to-End Latency:** 119.44 ms

*Because Face Detection triggers selectively (e.g. only on Zone Intruders) and terminates after a 5-frame sampling burst, its overhead is entirely bounded. The baseline latency is preserved for all other unflagged tracks.*

### Resource Utilization
- **Average CPU Usage:** ~345% (relative to process)
- **Average RAM Usage:** ~374 MB
- **GPU Usage:** N/A (CPU execution mode)

*Note: Benchmarks were run using SimulatedCamera in a pure-Python execution mode. Overhead will vary based on hardware acceleration (TensorRT) and real video decoding.*

### Multi-Camera Scalability
- **1 Camera:** ~3.80 Total FPS
- **2 Cameras:** ~8.16 Total FPS
- **4 Cameras:** ~12.33 Total FPS
