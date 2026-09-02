# SIH PS187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance

## Problem Statement
Developing an intelligent video analytics platform using existing CCTV infrastructure to enhance border surveillance, providing real-time alerts for intrusions, loitering, and suspicious activities while minimizing false positives.

## Architecture
This project utilizes a **selective AI inference** pipeline:
- **Selective Specialist AI**: Triggers ANPR or Face evaluation only when specific contextual conditions are met (e.g. Zone Intrusion). Best-frame selection ensures efficiency.
- **Unified Camera Integration**: Natively streams MP4 files, RTSP streams, and physical IP CCTV. Multi-camera execution is fully isolated (a failure in CAM02 won't crash CAM01).
- **FastAPI Backend & React Dashboard**: Real-time event propagation via HTTP and live MJPEG streaming endpoints.

See `docs/architecture.md` for a detailed Mermaid diagram.

## Setup
```bash
python -m venv .venv
# Activate venv (.venv/Scripts/activate on Windows, source .venv/bin/activate on Unix)
pip install -r requirements.txt
```

## Running
```bash
# Backend
uvicorn backend.main:app --reload

# Tests
pytest
```
