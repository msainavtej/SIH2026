# BorderX (Smart India Hackathon 2026 - PS 26187)

BorderX is an edge-first, AI-powered smart border intrusion detection and surveillance system built for the Smart India Hackathon (Problem Statement 26187).

## Core Features
*   **Intelligent Object Detection**: Real-time identification of humans, vehicles, and objects using Ultralytics YOLOv8.
*   **Virtual Boundaries (Geofencing)**: Interactive dashboard to draw custom polygon boundaries on camera feeds. Automatically triggers intrusions if tracked objects cross the boundary.
*   **Risk Event Engine**: Evaluates intrusion severity based on rules (e.g., night-time movement, restricted zone entries).
*   **Evidence Management**: Captures real JPEG snapshots the moment an event is triggered. Includes a Storage Governance engine that automatically purges old footage to enforce disk budgets (e.g., strict 100MB constraints).
*   **Cross-Camera Spatial-Temporal Correlation**: Links tracking IDs across adjacent cameras based on transition windows without relying on heavy Re-ID appearance models.
*   **Audit & Archive Logs**: Immutable logging of operator actions (e.g., event dismissals, system factory resets) separated from system diagnostic logs.

## Tech Stack
*   **Frontend**: React, Vite, HTML5 Canvas/SVG Overlay.
*   **Backend**: Python, FastAPI, Uvicorn.
*   **Computer Vision**: OpenCV, Ultralytics YOLOv8, SORT Object Tracking.
*   **Database & Storage**: SQLite (Metadata & Audit Trails), Local File System (Images/Video).

## Getting Started

### 1. Backend Setup
Make sure you have Python 3.10+ installed.

```bash
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI Server
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup
Make sure you have Node.js installed.

```bash
# Navigate to the dashboard directory
cd dashboard

# Install packages
npm install

# Run the development server
npm run dev
```

### 3. Usage
Navigate to the frontend development URL (usually `http://localhost:5173`).
1. Upload a video file via the backend or use the simulated camera setup to mimic a live feed.
2. Go to the **Zone Management** tab to draw virtual borders.
3. Watch the **Operations** tab as YOLO tracking hits the borders and generates Evidence Snapshots!

