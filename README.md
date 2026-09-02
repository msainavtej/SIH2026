# BorderX

Edge-first AI surveillance and risk-event intelligence for remote, low-connectivity environments.

## Problem Statement

Remote border surveillance environments present unique challenges that standard cloud-dependent CCTV systems struggle to address:
- **Connectivity:** Remote locations often have limited, intermittent, or completely unavailable internet bandwidth, making continuous cloud video streaming impossible.
- **Manual Monitoring:** Human operators cannot effectively monitor dozens of raw video feeds continuously without fatigue.
- **Lack of Context:** Raw video does not automatically generate actionable, structured security events.
- **Evidence Management:** Important incidents need isolated, verifiable evidence for post-incident review.
- **Storage Constraints:** Edge systems have limited disk space, which can easily be overwhelmed by continuous video recording.
- **Traceability:** Surveillance operations require an audit trail to track what actions operators took and what automated decisions the system made.

## Our Solution

BorderX operates entirely at the edge, converting raw video feeds into structured, actionable security events. Instead of streaming video to the cloud, the system processes frames locally, tracks objects, and evaluates them against operator-defined virtual boundaries.

**Data Flow Sequence:**
Camera / Video Feed 
        ↓
Local AI Inference 
        ↓
Object Detection 
        ↓
Object Tracking 
        ↓
Zone / Risk Evaluation 
        ↓
Risk Event Generation 
        ↓
Evidence Snapshot 
        ↓
Event & Audit Storage 
        ↓
Operator Dashboard

## Key Features

- **Edge/Local Video Processing**: All inference runs locally without mandatory external network requests.
- **YOLO-Based Object Detection**: Uses Ultralytics YOLOv8 for real-time identification of humans and vehicles.
- **SORT-Based Object Tracking**: Assigns persistent track IDs across consecutive frames.
- **Virtual Restricted Zones**: Interactive polygon-based zone configuration via the React dashboard.
- **Intrusion Detection & Risk Engine**: Automatically evaluates tracks intersecting with configured zones and assigns risk scores.
- **Evidence Snapshot Capture**: Physically writes a JPEG snapshot to disk the moment an intrusion is triggered.
- **Event Archive**: Stores historical events with their context and snapshot links.
- **Storage Governance & Auto-Purge**: Strict disk capacity management (e.g., 100MB limit) that automatically purges oldest evidence to prevent disk exhaustion.
- **Audit Trail**: Immutable logging separated into `OPERATOR` and `SYSTEM` views for forensic traceability.
- **Cross-Camera Spatial-Temporal Correlation**: *(Partially implemented / prototype capability)* Foundation for linking tracking IDs across adjacent cameras based on transition time windows.

## Real-World Problems Solved

| Real-World Problem | BorderX Approach | Result |
|---|---|---|
| Limited connectivity | Local/edge processing | Surveillance intelligence can continue without mandatory cloud inference |
| Manual video monitoring | Automated detection and tracking | Operators receive structured events instead of watching every frame |
| Unauthorized zone entry | Configurable virtual boundaries | System can generate intrusion events automatically |
| Lack of incident evidence | Automatic evidence snapshots | Events have visual JPEG evidence for immediate review |
| Storage limitations | Storage governance and auto-purge | Edge storage is strictly managed according to configured budget limits |
| Difficult incident investigation | Event archive + audit trail | Operators can quickly review historical activity and actions |

## System Architecture

```text
                           BORDERX
                              │
              ┌───────────────┴───────────────┐
              │                               │
        CAMERA / VIDEO                   OPERATOR
              │                               │
              ▼                               ▼
      ┌────────────────┐              ┌───────────────┐
      │ Camera Manager │              │ React + Vite  │
      │ / Video Input  │              │ Command Center│
      └───────┬────────┘              └───────┬───────┘
              │                               │
              ▼                               │
      ┌────────────────┐                      │
      │ OpenCV / Frame │                      │
      │ Processing     │                      │
      └───────┬────────┘                      │
              │                               │
              ▼                               │
      ┌────────────────┐                      │
      │ YOLO Inference │                      │
      │ Object Detect  │                      │
      └───────┬────────┘                      │
              │                               │
              ▼                               │
      ┌────────────────┐                      │
      │ SORT Tracking  │                      │
      └───────┬────────┘                      │
              │                               │
              ▼                               │
      ┌────────────────┐                      │
      │ Risk / Event   │◄─────────────────────┤
      │ Engine         │                      │
      └───────┬────────┘                      │
              │                               │
       ┌──────┴─────────┐                     │
       ▼                ▼                     │
┌─────────────┐  ┌───────────────┐            │
│ Evidence /  │  │ Event / Audit │            │
│ Snapshots   │  │ Persistence   │            │
└──────┬──────┘  └───────┬───────┘            │
       │                 │                    │
       └─────────────────┴────────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │ FastAPI REST API │
                └──────────────────┘
```

## Detailed Architecture Components

### 1. Camera / Input Layer
Currently supports file-based video uploads (MP4/AVI) and simulated blank feeds for testing. These feeds are ingested and managed by the `CameraManager`.

### 2. Frame Processing
OpenCV handles frame extraction, resizing, and rendering of bounding boxes/tracking IDs for the live stream endpoint.

### 3. AI Inference
The system uses an off-the-shelf Ultralytics YOLOv8 Nano (`yolov8n.pt`) model for rapid, lightweight 2D bounding box extraction. 

### 4. Object Tracking
Simple Online and Realtime Tracking (SORT) is used to assign IDs to bounding boxes across frames. This allows the system to monitor an object's trajectory rather than treating every frame as a unique, independent detection.

### 5. Risk / Event Engine
Evaluates: `Detection → Track → Zone/Context Evaluation → Risk Condition → Event`.
If a tracked person enters a configured polygon zone, the Risk Engine generates a "Virtual Boundary Intrusion" string, assigns a Risk Score, and elevates the track to an Active Event.

### 6. Evidence System
At the exact moment a track triggers an event condition, the system extracts the current OpenCV frame and writes it as a JPEG file to the local disk, linked via `evidence_path`.

### 7. Storage Governance
An active background monitor that tracks the `storage/evidence/` directory byte size. If the size exceeds the configured budget, it identifies the oldest, lowest-priority events, unlinks them from the SQLite database, and physically deletes the images. It also handles orphan file detection and full factory resets.

### 8. Audit System
Maintains a permanent ledger of actions in SQLite. The React UI separates these into `OPERATOR` (e.g., event review, zone creation) and `SYSTEM` (e.g., auto-purge triggers, startup routines) tabs.

### 9. API Layer
FastAPI exposes RESTful endpoints for camera ingestion, event querying, evidence retrieval (securely mapped by event ID), and analytics.

### 10. Frontend
A React + Vite Single Page Application (SPA) providing an Operator Dashboard, Live View, Zone Management, Event Archive, and System Insights.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React | Operator dashboard |
| Build Tool | Vite | Frontend development/build |
| Backend | Python | Core backend and AI orchestration |
| API | FastAPI | REST API |
| Computer Vision | OpenCV | Frame/video processing |
| Object Detection | Ultralytics YOLOv8 | Object detection |
| Tracking | SORT | Multi-frame object tracking |
| Database | SQLite | Local event/configuration persistence |
| Storage | Local filesystem | Evidence snapshots storage |

## Why This Architecture?

### Why edge-first?
Reduces dependency on network connectivity, enabling surveillance intelligence to continue operating in austere environments without mandatory cloud inference.

### Why YOLO?
Provides high-speed, real-time object detection suitable for CPU or entry-level edge AI accelerators.

### Why SORT?
Lightweight tracking maintains persistent track IDs over short durations without the massive computational overhead of appearance-based Re-ID embeddings.

### Why FastAPI?
Excellent performance, simple asynchronous routing, and native integration with Python ML/AI libraries.

### Why SQLite?
A lightweight, serverless local database is perfect for an edge prototype deployment, requiring zero complex setup while providing SQL query capabilities for event archives.

### Why React?
Enables building a highly interactive, state-driven dashboard visualization for operators.

## Data Flow

```text
Camera
  ↓
Frame
  ↓
Detection
  ↓
Tracking
  ↓
Zone Evaluation
  ↓
Risk Event
  ├──→ Event Metadata
  ├──→ Evidence Snapshot
  └──→ Audit Record
             ↓
          SQLite
             ↓
         FastAPI
             ↓
      React Dashboard
```

## Event Lifecycle

1. Frame captured via CameraManager.
2. Objects detected by YOLOv8.
3. Objects tracked by SORT.
4. Track evaluated against configured polygon zones.
5. Risk event generated upon intersection.
6. Evidence snapshot captured physically to disk.
7. Event metadata and snapshot path persisted in SQLite.
8. Evidence securely exposed through API.
9. Operator reviews event on the React Dashboard.
10. Event participates in storage governance (auto-purge) and archive lifecycle.

## Storage Governance

To prevent the edge node from exhausting disk space:
- **Storage Capacity:** Configurable byte limit (currently defaults to 100MB for prototype testing).
- **Auto-Purge Behavior:** If the budget is exceeded, the system automatically deletes the oldest `RESOLVED` or `DISMISSED` evidence snapshots.
- **Orphan Detection:** On startup, the system scans the physical directory for files not linked in the SQLite database and gracefully scrubs them.
- **Factory Reset:** Completely obliterates the physical `storage/evidence` directory and resets the SQLite tables to return the system to an empty state.

## Security & Privacy Design

- **Implemented:**
  - Local processing (No mandatory cloud outbound streaming).
  - No facial recognition active in the primary intrusion pipeline.
  - Evidence access is restricted through specific Event ID API lookups rather than arbitrary file path concatenation.
  - Immutable audit logging for operator actions.

- **Future Hardening:**
  - Production-grade Authentication (Currently bypasses with dummy "admin123").
  - Role-Based Access Control (RBAC).

## Current Limitations

- Prototype deployment currently targets standard local/edge environments (Windows/Linux PC) rather than embedded SOCs.
- Production-grade authentication/authorization is omitted for prototype speed.
- Camera hardware integration relies on file uploads/RTSP stubs; direct ONVIF/hardware integration requires specific environment adapters.
- Model accuracy relies on the default YOLOv8 Nano weights and has not been fine-tuned for specific border environments.
- Low-light, extreme weather, and heavy occlusion conditions will degrade detection accuracy.
- Cross-camera identity continuity has limitations without stronger feature-based re-identification.
- Hardware-specific optimization for NVIDIA Jetson/TensorRT is not yet implemented.

## Future Enhancements

- NVIDIA Jetson / TensorRT optimization for high-FPS edge inference.
- Hardware camera / ONVIF integration.
- Stronger cross-camera re-identification (e.g., BoT-SORT / OSNet).
- Encrypted evidence storage on disk.
- Role-based access control and OAuth integrations.
- Tamper-evident audit storage (e.g., cryptographic hashing of log rows).
- Offline synchronization (store-and-forward to central command when connectivity resumes).

## Deployment

### Local Development

**Backend:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd dashboard
npm install
npm run dev
```

### Edge Deployment
**Planned / Deployment Target:** NVIDIA Jetson Nano / Orin series using Docker containers (Dockerfile/Compose setup pending).

## Project Structure

```text
BorderX/
├── ai/
│   ├── detection/       # YOLO wrappers
│   ├── inference/       # AI pipeline orchestration
│   └── tracking/        # SORT tracker implementation
├── backend/
│   ├── api/             # FastAPI routers
│   ├── schemas/         # Pydantic models
│   ├── camera_manager.py
│   └── storage_manager.py
├── camera/              # Camera ingestion adapters
├── configs/             # YAML configurations
├── dashboard/           # React + Vite frontend
│   └── src/
├── docs/                # Architecture documentation
├── intelligence/        # Risk, Rules, and Zone engines
├── scripts/             # Utility scripts
├── simulator/           # Test fixtures and simulated inputs
├── storage/             # Local database and physical evidence
└── README.md
```

## API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/cameras` | List connected cameras and status |
| GET | `/api/cameras/{id}/stream` | MJPEG live video stream |
| POST | `/api/cameras/upload` | Upload a test video file |
| GET | `/api/cameras/{id}/zones` | List virtual boundaries |
| POST | `/api/cameras/{id}/zones` | Add a virtual boundary |
| DELETE | `/api/cameras/{id}/zones/{zone_id}` | Remove a virtual boundary |
| GET | `/api/events` | List historical and active events |
| GET | `/api/events/{id}/evidence` | Retrieve JPEG snapshot for event |
| GET | `/api/audit_logs` | Retrieve system and operator logs |
| DELETE | `/api/audit_logs` | Perform system Factory Reset |

## SIH Relevance

BorderX directly addresses Smart India Hackathon Problem Statement 26187 by demonstrating a localized, highly-autonomous surveillance processing architecture. Instead of streaming high-bandwidth video over fragile border networks, BorderX extracts the semantic intelligence (Risk Events, Intrusion Context, JPEGs) locally. This drastically reduces bandwidth requirements, alerts operators proactively to actual intrusions, and automatically enforces hardware storage limits—making it a practical deployment model for rugged border environments.

## Innovation

BorderX differs from a standard CCTV dashboard through its edge-first data processing pipeline. Raw video is never sent over the network. Instead, the system relies entirely on AI perception, persistent tracking, and contextual zone evaluation performed on the node itself. The innovation lies in the system architecture: prioritizing structured, queryable risk events and isolated JPEG evidence over raw video streaming, which makes the system uniquely resilient to network instability.

## Demo Scenario

1. Operator navigates to the Command Center dashboard.
2. Operator loads a surveillance video via the backend upload API.
3. Operator navigates to the Zone Management tab and defines a restricted polygon over the feed.
4. The AI detects a person in the video.
5. The Tracker assigns a persistent track ID.
6. The Track enters the restricted polygon zone.
7. The Risk Engine triggers a "Virtual Boundary Intrusion" event.
8. The Storage Engine captures an immediate JPEG evidence snapshot.
9. The Dashboard automatically displays the active event, reason, and visual evidence.
10. The Audit Trail permanently records the system action, while Storage Governance ensures the disk budget is respected.

## Performance / Optimization

- **Lightweight Tracking:** Uses SORT (Kalman filters + Hungarian algorithm) instead of heavy neural Re-ID models to maintain high FPS on CPU.
- **Local Processing:** Eradicates network latency for AI inference.
- **Storage Auto-Purge:** Proactively guards against OS crashes due to disk exhaustion.
- **Event Deduplication:** Evaluates tracks iteratively to prevent flooding the database with identical events for the same object.

*Formal benchmark results (FPS, exact memory overhead, accuracy matrices) are not yet available.*

## Testing & Validation

The following flows have been functionally verified in the prototype:
- API health and routing integrity.
- Video upload and simulated ingestion pipeline.
- Interactive zone creation via SVG mapping.
- Intrusion event generation triggered by tracked objects.
- Real-time snapshot creation via OpenCV.
- Secure evidence retrieval mapping (immune to path traversal).
- Storage auto-purge and directory cleanup.
- Operator vs. System audit filtering.
- Restart persistence for zones and events via SQLite.

## Screenshots

*(Placeholder: Screenshots of the Command Center, Zone Management, and Audit Log will be added here upon final UI freeze.)*

## Conclusion

BorderX transforms raw camera feeds into actionable, explainable security events while keeping the core intelligence close to the surveillance environment. 

**Current Status:** SIH Prototype / Demonstration Build

