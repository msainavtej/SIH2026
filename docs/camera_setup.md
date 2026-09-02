# PS187 Camera Setup & Configuration

The PS187 architecture natively supports multiple types of cameras through a unified abstraction layer, making it easy to test with files before deploying to physical IP CCTV networks.

## 1. MP4 Development Mode
For repeatable development and testing, you can use `.mp4` video files. The `FileCamera` source simulates a continuous stream by automatically looping the file when it reaches the end.
```yaml
cameras:
  - id: CAM_DEV
    source_type: file
    url: "test_video.mp4"
    enabled: true
```

## 2. RTSP Test Mode
You can simulate a network camera by streaming an MP4 file over RTSP locally using tools like `mediamtx` or `vlc`.
```bash
# Example using cvlc (VLC)
cvlc test.mp4 --sout '#rtp{sdp=rtsp://:8554/stream}' --loop
```
Configure `cameras.yaml` to point to `rtsp://localhost:8554/stream`.

## 3. Phone-Camera Testing
You can turn your smartphone into a temporary IP camera for testing real-world angles and networking:
1. Ensure your PC and phone are on the same Wi-Fi network.
2. Install an app like **IP Webcam** (Android) or **Live Reporter** (iOS) that provides an RTSP stream.
3. Configure `cameras.yaml`:
```yaml
  - id: PHONE_CAM
    source_type: rtsp
    url: "rtsp://192.168.1.100:8080/h264_ulaw.sdp"
```

## 4. Physical IP-Camera Testing
When connecting to physical border surveillance CCTV infrastructure:
1. Ensure the camera supports RTSP.
2. Verify the PC is on the same VLAN/subnet or has correct routing to the camera IPs.
3. For security, never hardcode passwords in the YAML file. Use environment variables:
```yaml
  - id: CCTV_EAST
    source_type: rtsp
    url: "${RTSP_CCTV_EAST}" # e.g. rtsp://admin:secret@10.0.0.5:554/stream1
```

## 5. Multi-Camera Configuration
To run multiple cameras simultaneously, simply list them in `configs/cameras.yaml`.
The `CameraManager` isolates their inference pipelines and track IDs (e.g., `CAM01-P27`) so a failure or stutter in `CAM02` will NOT affect `CAM01`.

## 6. Troubleshooting RTSP
Use the `test_camera.py` script to verify connectivity and stream health independently of the AI pipeline:
```bash
python scripts/test_camera.py --camera CAM01
```

**Common issues:**
- `OFFLINE`: Check if the IP is pingable and the RTSP port (usually 554) is open.
- `DEGRADED`: The connection is established, but frames are arriving too slowly or being dropped. Check bandwidth/Wi-Fi signal.
- **Authentication**: Ensure the username and password in the RTSP URL are URL-encoded if they contain special characters.
