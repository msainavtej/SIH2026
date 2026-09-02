# Cross-Camera Spatial-Temporal Correlation Architecture & Codebase Survey Report

## 1. Observation

Direct code inspection across all modules in `C:\Users\HEMANTH\Desktop\SKYNET` reveals the following architectural components, file locations, line numbers, and existing data structures:

### 1.1 Data Models & Schemas
- **`backend/schemas/events.py:5-9`**: Defines `TrackedObject`:
  ```python
  class TrackedObject(BaseModel):
      track_id: str
      object_type: str
      confidence: float
      bbox: List[int] = Field(description="Bounding box [x1, y1, x2, y2]")
  ```
- **`backend/schemas/events.py:11-38`**: Defines `EventSchema`:
  ```python
  class EventSchema(BaseModel):
      event_id: str
      camera_id: str
      timestamp: datetime
      start_time: datetime
      end_time: Optional[datetime] = None
      status: str = "ACTIVE" # CANDIDATE, ACTIVE, RESOLVED, DISMISSED
      track_id: str
      object_type: str
      confidence: float
      plate: Optional[str] = None
      plate_confidence: Optional[float] = None
      plate_observations: Optional[int] = 0
      zone: Optional[str] = None
      direction: Optional[str] = None
      dwell_seconds: Optional[int] = 0
      has_face: Optional[bool] = False
      face_score: Optional[int] = None
      face_category: Optional[str] = None
      risk_score: int = Field(default=0, ge=0, le=100)
      max_risk_score: int = Field(default=0, ge=0, le=100)
      risk_level: str
      reasons: List[str]
      score_breakdown: Optional[dict] = None
      snapshot_path: Optional[str] = None
      evidence_path: Optional[str] = None
      is_held: bool = False
  ```
- **`backend/api/events_store.py:18-43`**: Defines SQLite schema in `storage/events.db`:
  - Table `events`: `(event_id TEXT PRIMARY KEY, camera_id TEXT, timestamp TEXT, object_type TEXT, track_id TEXT, risk_level TEXT, risk_score REAL, status TEXT, data TEXT)`
  - Table `audit_logs`: `(id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, timestamp TEXT, operator TEXT, action TEXT, reason TEXT, notes TEXT)`

### 1.2 Ingestion & Tracking Pipeline
- **`camera/base.py:5-54`**: `CameraSource` abstract base class with `connect()`, `read()`, `is_online()`, `reconnect()`, `release()`, and `get_health()`.
- **`camera/simulated_camera.py:6-38`**, **`camera/file_camera.py:5-58`**, **`camera/rtsp_camera.py:6-80`**: Implementations of camera sources.
- **`ai/tracking/tracker.py:4-40`**: `ByteTracker` using Ultralytics YOLOv8n tracking (`self.model.track(frame, persist=True, tracker="bytetrack.yaml")`). Detects classes `[0, 2, 3, 5, 7]` (`person`, `car`, `motorcycle`, `bus`, `truck`) and prefixes track IDs with initial (`P1`, `C2`, etc.).
- **`ai/tracking/trajectory.py:4-56`**: `TrajectoryManager` maintains a deque of `[center_x, center_y]` with `max_history=30` and `cleanup(timeout_sec=5.0)`.
- **`ai/inference/pipeline.py:13-150`**: `InferencePipeline` runs tracking, updates trajectories, computes zones via `ZoneManager`, direction via `DirectionEstimator`, dwell via `DwellTracker`, selectively triggers `ANPRPipeline` and `FacePipeline`, and returns `(frame, enriched_tracks, status)`.

### 1.3 Multi-Camera Management & Event Processing
- **`backend/camera_manager.py:25-56`**: `CameraManager.load_cameras()` parses `configs/cameras.yaml`, instantiates camera sources, `InferencePipeline` per camera, and `EventEngine(risk_engine)` per camera.
- **`backend/camera_manager.py:64-100`**: `_run_pipeline(cid)` loop:
  - Line 86-88: Prepends camera ID to track IDs:
    ```python
    for t in tracks:
        if not str(t['track_id']).startswith(f"{cid}-"):
            t['track_id'] = f"{cid}-{t['track_id']}"
    ```
  - Line 90-93: Processes tracks through `event_engine.process_tracks(cid, tracks)` and saves emitted events into `events_db.append(e)`.
- **`intelligence/event_engine.py:12-136`**: `EventEngine.process_tracks()`:
  - Manages track lifecycle: `active_events` dict (`track_id -> EventSchema`).
  - Generates event ID `EVT-YYYYMMDD-xxxxxx`, generates mock evidence file via `storage_manager.generate_mock_evidence(eid)`.
  - Evaluates risk score/level/reasons via `risk_engine.evaluate(event_type, context)`.
  - Detects lost tracks (lines 127-134) and transitions them to `status = "RESOLVED"` with `end_time`.

### 1.4 Storage Governance & Audit Trail
- **`backend/storage_manager.py:8-77`**: `StorageManager` governs `storage/evidence/` with a 50MB demo budget cap (`max_budget_mb=50`):
  - Line 48-76: `enforce_retention()` triggers when disk usage > 90% budget.
  - Line 56: Excludes held events (`e.is_held == True`).
  - Line 59-65: Sorts purge-eligible events by tier priority: `DISMISSED` (tier 0) -> `LOW`/`NORMAL` (tier 1) -> `MEDIUM` (tier 2) -> `HIGH`/`CRITICAL` (tier 3), then oldest timestamp first.
  - Line 72-74: Physically deletes evidence file via `events_db.delete_evidence_files()`, and records immutable audit log with operator `"SYSTEM_AUTO_PURGE"`, action `"AUTO_PURGED"`.
- **`backend/api/events.py:34-49`**: `/api/events/{event_id}/resolve` sets `status = "DISMISSED"`, drops raw evidence footage (`events_db.delete_evidence_files`), and logs audit entry (`events_db.log_audit(event_id, req.operator, 'REVIEWED', req.reason, req.notes)`).
- **`backend/api/storage.py:34-42`**: `/api/events/{event_id}/hold` sets `is_held = True` and logs audit entry with action `"HELD"`.

### 1.5 Dashboard Frontend
- **`dashboard/src/App.jsx:8-661`**: React SPA:
  - Lines 182-224: Active Events table showing Time, Camera, Object, Risk Level Badge, and Details.
  - Lines 272-290: Event Archive list.
  - Lines 295-335: Audit & Review Log view showing timestamp, operator, action badge, reason, notes/event_id.
  - Lines 372-404: Storage Governance breakdown (Live Usage bar, Routine / Confirmed / Held counts).
  - Lines 446-560: Event Investigation detail modal (Live/archived frame, AI insights, Primary subject, Plate/Face confidence, Audit trail, Escalate/Resolve/Hold buttons).

---

## 2. Logic Chain

From these direct observations, we construct the step-by-step logic for integrating the cross-camera spatial-temporal correlation engine:

```
[Observation 1.2: InferencePipeline tracks bboxes & trajectories per frame]
                              │
                              ▼
[Observation 1.3: CameraManager isolates track IDs as 'CAM01-P1' & 'CAM02-P2']
                              │
                              ▼
[Observation 1.3: EventEngine tracks active vs lost tracks per camera]
                              │
                              ▼
   [Step 1: Track Exit / Entry Detection via Edge Boundary Analyzer]
   - Camera 1 (CAM01): Track reaches configured exit edge (e.g. RIGHT: x > 600 or dx > 0 near edge)
     and disappears -> Emits ExitEvent(track_id='CAM01-P1', object_type='person', edge='RIGHT', timestamp=t_exit)
   - Camera 2 (CAM02): Track appears at configured entry edge (e.g. LEFT: x < 40)
     -> Emits EntryEvent(track_id='CAM02-P2', object_type='person', edge='LEFT', timestamp=t_entry)
                              │
                              ▼
   [Step 2: Cross-Camera Spatial-Temporal Correlation Engine]
   - When ExitEvent occurs on CAM01, open correlation window for configured adjacency (CAM01 -> CAM02).
   - Core transit window: [t_exit + min_transit, t_exit + max_transit] (e.g., 3s to 15s).
   - Grace transit window: up to max_transit * (1 + grace_factor) (e.g., up to 22.5s).
   - When EntryEvent occurs on CAM02:
     * Check active correlation windows.
     * Check Class Match (e.g., person == person, car == car). Mismatch -> NO LINK.
     * Check Timing & Edge Vector:
       - HIGH: class match + correct configured exit & entry edges + core transit window [3s, 15s].
       - MEDIUM: class match + core transit window [3s, 15s], but edge vector ambiguous/missing.
       - LOW: class match + grace window (15s, 22.5s], OR edge+timing match with borderline class confidence.
       - Below LOW / Exceeded Grace / Mismatch: NO LINK (independent events remain unlinked).
                              │
                              ▼
   [Step 3: Unified Correlated Incident Generation]
   - Create or update unified Incident / Event linking both track IDs:
     primary_track_id: 'CAM01-P1', correlated_track_id: 'CAM02-P2'
     camera_id: 'CAM02' (or 'CAM01+CAM02'), reasons: ['Cross-camera transit CAM01 -> CAM02', 'Timing match 4.2s']
     correlation_confidence: 'HIGH' / 'MEDIUM' / 'LOW'
     risk_level: 'HIGH' (or escalated per rule)
   - Resave to events_db via SQLiteEventStore.
                              │
                              ▼
   [Step 4: Storage Governance & Audit Trail Preservation (V8)]
   - Correlated Incident continues to inherit EventSchema properties (evidence_path, is_held, status).
   - StorageManager auto-purge and hold/resolve endpoints operate identically without regressions.
                              │
                              ▼
   [Step 5: Dashboard UI Updates]
   - Display categorical confidence band ('HIGH', 'MEDIUM', 'LOW') prominently on Event cards & Incident detail.
   - Text strictly adheres to non-identity phrasing ("Track #CAM02-P2 correlated with #CAM01-P1 [HIGH]", NO "same person confirmed").
```

---

## 3. Detailed Architecture Findings & Insertion Points

### 3.1 Data Model Extensions (`backend/schemas/events.py`)
To represent unified cross-camera incidents without breaking single-camera compatibility, `EventSchema` can be enriched with optional correlation fields (or a unified `IncidentSchema` inheriting/wrapping it):
- `correlated_track_id: Optional[str] = None` (e.g., `"CAM01-P1"`)
- `source_camera_id: Optional[str] = None` (e.g., `"CAM01"`)
- `target_camera_id: Optional[str] = None` (e.g., `"CAM02"`)
- `transit_duration_seconds: Optional[float] = None` (e.g., `5.4`)
- `correlation_confidence: Optional[str] = None` (`"HIGH"`, `"MEDIUM"`, `"LOW"`, `None`)
- `correlation_reasons: Optional[List[str]] = None`

### 3.2 Adjacency Configuration (`configs/adjacency.yaml`)
External configuration specification:
```yaml
adjacency_map:
  enabled: true
  camera_from: "CAM01"
  camera_to: "CAM02"
  exit_edge: "RIGHT"        # RIGHT | LEFT | TOP | BOTTOM
  entry_edge: "LEFT"        # RIGHT | LEFT | TOP | BOTTOM
  transit_window:
    min_seconds: 3.0
    max_seconds: 15.0
    grace_window_percent: 50.0  # allows up to 22.5s for LOW band
  edge_boundary_margin_px: 40
  min_track_confidence: 0.50
  bands:
    high:
      require_exact_edges: true
      require_core_window: true
      require_class_match: true
    medium:
      allow_ambiguous_edge: true
      require_core_window: true
      require_class_match: true
    low:
      allow_grace_window: true
      require_class_match: true
```

### 3.3 Exact Insertion Points

| Module / Component | Target File | Insertion Point & Responsibility |
|--------------------|-------------|-----------------------------------|
| **Boundary & Edge Analyzer** | `intelligence/boundary.py` (new) or `intelligence/direction.py` | Detects when a track's trajectory approaches or crosses configured camera boundaries (`LEFT`, `RIGHT`, `TOP`, `BOTTOM`). Computes normalized exit/entry edge vectors. |
| **Cross-Camera Correlation Engine** | `intelligence/correlation.py` (new) | Manages active correlation candidate windows, handles `on_track_exit(camera_id, track)` and `on_track_entry(camera_id, track)`. Applies categorical confidence banding (`HIGH`, `MEDIUM`, `LOW`, `NONE`). Prunes expired windows to prevent unbounded memory growth. |
| **Pipeline Integration** | `backend/camera_manager.py` (lines 55, 84-95) | Holds shared instance of `SpatialTemporalCorrelationEngine`. When `_run_pipeline(cid)` processes tracks, passes newly detected entries and lost/exiting tracks to the correlation engine. Emits unified correlated incidents to `events_db`. |
| **Event Engine Integration** | `intelligence/event_engine.py` (lines 127-135) | When a track is lost or exits the frame, triggers correlation exit hook before resolving single-camera event state. |
| **Storage & Audit Persistence** | `backend/api/events_store.py` & `backend/storage_manager.py` | Stores unified incidents in `storage/events.db` and attaches mock evidence for storage governor tests. |
| **Dashboard UI** | `dashboard/src/App.jsx` (lines 203-216, 484-518) | Displays `correlation_confidence` badge (`HIGH`/`MEDIUM`/`LOW`) on Active Events cards, Event Archive, and the Incident Detail modal. |

### 3.4 Verification Requirements (V1 - V8) Alignment
1. **V1. Positive Match**: Track exits `CAM01` RIGHT edge -> compatible track enters `CAM02` LEFT edge at $t=5.0s$ -> Incident created linking both IDs with `correlation_confidence == 'HIGH'`.
2. **V2. Class Mismatch**: `person` exits `CAM01` -> `car` enters `CAM02` at $t=5.0s$ -> NOT linked.
3. **V3. Timing Boundaries**:
   - Entry at $t = 2.9s$ ($3.0 - 0.1s$) -> NOT linked.
   - Entry at $t = 3.0s$ (min inclusive) -> linked (`HIGH`).
   - Entry at $t = 15.0s$ (max inclusive) -> linked (`HIGH`).
   - Entry at $t = 15.1s$ ($15.0 + 0.1s$) -> linked as `LOW` (grace window).
   - Entry at $t = 22.6s$ ($22.5 + 0.1s$, exceeding grace) -> NOT linked.
4. **V4. Edge Mismatch**: Track exits through TOP/BOTTOM instead of configured RIGHT edge -> downgraded to `MEDIUM` or `LOW`, never silently promoted to `HIGH`.
5. **V5. Integration - 2-Camera Live Simulator Run**: Deterministic scenario walking synthetic object across `CAM01` -> `CAM02` with live dashboard display within 2s, reproducible 3 times consecutively.
6. **V6. Concurrency / Anti-Double-Link**: Two candidate tracks near exit at once -> engine matches optimal temporal candidate or declines ambiguous links; zero double-linking of one exit to multiple entries.
7. **V7. Memory Cleanup**: Open correlation windows without matching entry automatically pruned after $t_{max} \times 1.5$; memory remains $O(1)$ under continuous unmatched exits.
8. **V8. Regression**: Single camera event pipeline, ANPR voting, Face assessment, storage governor auto-purge, hold, and immutable audit trail all pass with zero regressions.

---

## 4. Caveats

- **No Appearance-Based Re-ID**: In strict accordance with R3 and Acceptance Criteria, no visual feature extraction models (such as OSNet, BoT-SORT appearance embeddings, or deep feature extractors) should be imported or invoked. The correlation relies purely on spatial-temporal geometry, transit duration, bounding box vectors, and object class matching.
- **Camera Source Submodule Reference**: In `tests/unit/test_camera.py`, `from camera.camera_source import SimulatedCamera` was noted. Ensure `camera/__init__.py` or alias handles module resolution so existing unit tests pass cleanly.
- **Single 2-Camera Pair Assumption**: R1 specifies exactly 2 cameras (`CAM-01` to `CAM-02`). No N-camera graph solver is required or permitted.

---

## 5. Conclusion

The existing codebase is well-structured, modular, and event-driven. The insertion points for the 2-camera spatial-temporal correlation engine are cleanly identified in `intelligence/` (new correlation engine and edge boundary detector) and wired through `backend/camera_manager.py`. The data models in `backend/schemas/events.py` and `backend/api/events_store.py` seamlessly accommodate correlated incidents without breaking storage governance or the audit trail.

---

## 6. Verification Method

To independently verify the findings in this report:

1. **Verify Schema & Store**:
   - Inspect `backend/schemas/events.py:11` and `backend/api/events_store.py:18` for `EventSchema` and SQLite table definitions.
2. **Verify Multi-Camera Pipeline & Track Isolation**:
   - Inspect `backend/camera_manager.py:84-94` to verify camera ID prefixing and track feeding.
3. **Verify Storage Governance & Audit Retention**:
   - Inspect `backend/storage_manager.py:47-76` to verify 90% budget threshold, tier sorting (0 to 3), `is_held` protection, and audit logging.
4. **Verify Scenarios & Unit Tests**:
   - Inspect `simulator/scenarios/test_scenarios.py:1-418` for baseline test assertions.
