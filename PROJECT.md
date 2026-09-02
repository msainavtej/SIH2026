# Project: SKYNET Cross-Camera Spatial-Temporal Correlation Engine

## Architecture

The Cross-Camera Spatial-Temporal Correlation Engine links track segments across exactly two adjacent cameras (`CAM01` and `CAM02`) based purely on external adjacency geometry, transit time windows, object classification consistency, and spatial entry/exit bounding box vectors. It strictly avoids any appearance-based Re-ID embeddings (e.g., BoT-SORT features, CNN embeddings) and N-camera graph structures.

```
+-----------------------------------------------------------------------------------+
|                                SKYNET ARCHITECTURE                                |
+-----------------------------------------------------------------------------------+

   +--------------------+                      +--------------------+
   | CAM01 Video Stream |                      | CAM02 Video Stream |
   +---------+----------+                      +---------+----------+
             |                                           |
             v                                           v
   +---------+----------+                      +---------+----------+
   | InferencePipeline  |                      | InferencePipeline  |
   | (YOLOv8 + Tracking)|                      | (YOLOv8 + Tracking)|
   +---------+----------+                      +---------+----------+
             | (tracks: 'CAM01-P1')                      | (tracks: 'CAM02-P2')
             v                                           v
   +---------+-------------------------------------------+----------+
   |                         CameraManager                          |
   |   - Enriches tracks with camera prefix                         |
   |   - Interacts with EventEngine & CorrelationEngine             |
   +---------+-------------------------------------------+----------+
             |                                           |
             +---------------------+---------------------+
                                   |
                                   v
             +-------------------------------------------+
             |  SpatialTemporalCorrelationEngine         |
             |  (intelligence/correlation.py)            |
             |                                           |
             |  1. Configuration (configs/adjacency.yaml)|
             |     - Pair: CAM01 -> CAM02                |
             |     - Exit Edge: RIGHT (x >= 0.9*W)       |
             |     - Entry Edge: LEFT (x <= 0.1*W)       |
             |     - Transit: [3.0s, 15.0s] (Grace 22.5s)|
             |  2. Boundary Analyzer (Spatial Edges)     |
             |  3. Temporal Window Lifecycle & GC        |
             |  4. Categorical Confidence Banding:       |
             |     HIGH, MEDIUM, LOW, NONE               |
             |  5. 1-to-1 Disambiguation & Tie-Break     |
             +---------------------+---------------------+
                                   |
                                   v
             +-------------------------------------------+
             |             Unified Incident              |
             |  - Links 'CAM01-P1' & 'CAM02-P2'          |
             |  - Confidence: HIGH/MEDIUM/LOW            |
             |  - No "confirmed person" claims           |
             +---------------------+---------------------+
                                   |
                    +--------------+--------------+
                    v                             v
   +--------------------------------+   +--------------------+
   | SQLiteEventStore / StorageGov  |   | React Dashboard UI |
   | - 3-tier storage retention     |   | - Visible badge    |
   | - Immutable audit trail        |   | - Incident detail  |
   | - 50MB quota auto-purge        |   | - Live demo ~2s    |
   +--------------------------------+   +--------------------+
```

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1: External Adjacency Configuration | YAML schema (`configs/adjacency.yaml`) & Pydantic validation models (`AdjacencyPairConfig`) defining camera pairs, edges, transit bounds, and thresholds. | M1 | survey |
| 2 | F2: Spatial Edge Boundary & Velocity Analyzer | Spatial boundary intersection math and trajectory directional velocity verification for configured exit/entry edges (`RIGHT`, `LEFT`, `TOP`, `BOTTOM`). | M1 | survey |
| 3 | F3: Spatial-Temporal Correlation Engine Core | Temporal window lifecycle manager (`OPEN`, `CONSUMED`, `EXPIRED`), candidate evaluation, and deterministic garbage collection / memory bounding (V7). | M1 | survey |
| 4 | F4: Categorical Confidence Banding | Strict categorical confidence scoring (`HIGH`, `MEDIUM`, `LOW`, `NONE`) with zero raw percentages, no identity overclaims, and graceful downgrades (V1, V2, V3, V4). | M1 | survey |
| 5 | F5: Concurrency & Disambiguation Protocol | 1-to-1 matching invariant, time-closeness heuristic ($|\Delta t - t_{expected}|$), and tie-breaking link declination (V6). | M1 | survey |
| 6 | F6: Multi-Camera Pipeline Integration & Incident Linkage | Integration with `backend/camera_manager.py`, `intelligence/event_engine.py`, `backend/schemas/events.py`, and `backend/api/events_store.py`. | M2 | survey |
| 7 | F7: Storage Governance & Audit Trail Parity | Full preservation of 3-tier retention rules, 50MB quota auto-purge, operator hold exemptions, and immutable audit logs for correlated incidents (V8). | M2 | survey |
| 8 | F8: Live 2-Camera Simulator & Integration Scenario | Integration scenario simulating a subject walking from CAM01 to CAM02, reproducible 3 times consecutively with latency $\le 2.0s$ (V5). | M3 | survey |
| 9 | F9: Dashboard UI & Anti-Overclaim Compliance | Visible confidence band on Event cards & Incident detail modal; strict prohibition of "confirmed identity" / "same person" phrasing across UI and logs. | M3 | survey |
| 10 | F10: E2E Comprehensive Test Suite & Adversarial Hardening | Requirement-driven opaque-box test suite (Tiers 1-4) publishing `TEST_READY.md`, followed by Tier 5 adversarial hardening and Forensic Integrity Audit. | M_TEST / M4 | survey |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|--------------|--------|
| **M_TEST** | E2E Testing Suite (Tiers 1-4) | Requirement-driven test harness, test cases for V1-V8 and acceptance criteria, `TEST_INFRA.md`, `TEST_READY.md`. | none | DONE |
| **M1** | Configuration Schema, Spatial Boundary & Correlation Engine Core | F1, F2, F3, F4, F5: `configs/adjacency.yaml`, `intelligence/correlation.py`, `intelligence/boundary.py`, unit tests for V1, V2, V3, V4, V6, V7. | none | DONE |
| **M2** | Pipeline Integration, Schema Extensions, Storage & Audit Parity | F6, F7: `backend/schemas/events.py`, `backend/camera_manager.py`, `intelligence/event_engine.py`, `backend/api/events_store.py`, `backend/storage_manager.py`, regression V8. | M1 | DONE |
| **M3** | Live 2-Camera Simulator & Dashboard UI | F8, F9: `simulator/scenarios/two_camera_correlation.py`, `dashboard/src/App.jsx`, 3x reproducible walk test (V5), UI compliance. | M2 | DONE |
| **M4** | Final Acceptance, 100% E2E Pass & Adversarial Hardening | F10: Pass 100% of E2E test suite (Tiers 1-4), Tier 5 adversarial hardening with Challenger, Forensic Integrity Audit. | M_TEST, M3 | DONE |

---

## Interface Contracts

### 1. Adjacency Configuration Schema (`configs/adjacency.yaml`)
```yaml
adjacency_map:
  pair_id: "ADJ_CAM01_CAM02"
  enabled: true
  source_camera_id: "CAM01"
  target_camera_id: "CAM02"
  spatial_edges:
    source_exit_edge: "right"        # "left" | "right" | "top" | "bottom"
    target_entry_edge: "left"        # "left" | "right" | "top" | "bottom"
    edge_threshold_fraction: 0.10
    min_trajectory_points: 3
  transit_timing:
    min_transit_seconds: 3.0
    max_transit_seconds: 15.0
    grace_window_seconds: 7.5        # +50% beyond max_transit
    ambiguity_tie_threshold_s: 0.5
  confidence_rules:
    detection_conf_threshold: 0.50
    allow_ambiguous_edge_medium: true
    allow_grace_window_low: true
  lifecycle:
    gc_interval_seconds: 1.0
    max_active_windows: 200
```

### 2. Correlation Engine API (`intelligence/correlation.py`)
```python
class SpatialTemporalCorrelationEngine:
    def __init__(self, config_path: str = "configs/adjacency.yaml"):
        ...
    def on_track_exit(self, camera_id: str, track: dict, timestamp: float) -> Optional[CorrelationWindow]:
        """Called when a track exits or terminates on a camera."""
        ...
    def on_track_entry(self, camera_id: str, track: dict, timestamp: float) -> Optional[CorrelatedTrackLink]:
        """Called when a new track is initialized or enters a camera."""
        ...
    def evaluate_correlation(self, window: CorrelationWindow, entry_track: dict, entry_timestamp: float) -> Optional[CorrelatedTrackLink]:
        """Evaluates compatibility, timing, spatial edges, and assigns ConfidenceBand (HIGH, MEDIUM, LOW, or None)."""
        ...
    def cleanup_expired(self, current_timestamp: float) -> int:
        """Purges expired correlation windows beyond t_exit + max_transit + grace_window."""
        ...
```

### 3. Event / Incident Schema Extensions (`backend/schemas/events.py`)
```python
class EventSchema(BaseModel):
    event_id: str
    camera_id: str
    timestamp: datetime
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "ACTIVE"
    track_id: str
    object_type: str
    confidence: float
    risk_score: int
    risk_level: str
    reasons: List[str]
    # Cross-camera correlation extensions
    incident_id: Optional[str] = None
    correlation_confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    correlated_with_track: Optional[str] = None
    correlated_with_camera: Optional[str] = None
    transit_time_seconds: Optional[float] = None
    is_held: bool = False
    evidence_path: Optional[str] = None
```

---

## Code Layout

- `configs/adjacency.yaml` — External adjacency configuration file (owned by M1)
- `intelligence/correlation.py` — Spatial-temporal correlation engine and window manager (owned by M1)
- `intelligence/boundary.py` — Spatial edge boundary and directional velocity evaluator (owned by M1)
- `backend/schemas/events.py` — Event and Incident data models with correlation fields (owned by M2)
- `backend/camera_manager.py` — Multi-camera track routing and correlation engine integration (owned by M2)
- `intelligence/event_engine.py` — Single-camera event lifecycle with exit hooks (owned by M2)
- `backend/api/events_store.py` — SQLite persistence for events, incidents, and audit logs (owned by M2)
- `backend/storage_manager.py` — Storage governance 3-tier retention and auto-purge (owned by M2)
- `simulator/scenarios/two_camera_correlation.py` — 2-camera live walk simulation scenario (owned by M3)
- `dashboard/src/App.jsx` — React frontend displaying confidence badges without identity overclaims (owned by M3)
- `tests/unit/test_correlation_engine.py` — Unit tests for V1, V2, V3, V4, V6, V7 (owned by M1 / M_TEST)
- `tests/integration/test_two_camera_correlation.py` — Integration tests for V5 (owned by M3 / M_TEST)
- `tests/integration/test_regression.py` — Regression tests for V8 (owned by M2 / M_TEST)
- `tests/e2e/` — Comprehensive 4-tier E2E test suite (owned by M_TEST)
