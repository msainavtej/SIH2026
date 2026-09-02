# Cross-Camera Correlation Engine: Test Suite Survey & V1-V8 Verification Plan

## 1. Observation

### 1.1 Test Execution Environment
- **Operating System:** Windows (Shell: pwsh)
- **Virtual Environment Path:** `C:\Users\HEMANTH\Desktop\SKYNET\.venv`
- **Python Interpreter:** `C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe` (Version: Python 3.11.9)
- **Test Framework:** Pytest 9.1.1 (`pluggy-1.6.0`, `anyio-4.14.2`) located in `.venv\Lib\site-packages\pytest`
- **Installed Dependencies (`requirements.txt`):**
  ```
  fastapi, uvicorn[standard], pydantic, pydantic-settings, opencv-python-headless,
  numpy, torch, ultralytics, psutil, pytest, requests, pyyaml, websockets
  ```

### 1.2 Existing Test Suite Architecture & Locations
1. **`simulator/scenarios/test_scenarios.py` (32 scenarios total):**
   - **24 Core Single-Camera Pipeline Scenarios** (`run_all_scenarios()` lines 326–404):
     - Detections & Intrusions: *Normal pedestrian*, *Normal vehicle*, *Brief intrusion*, *Persistent intrusion*, *Night movement*, *Night + restricted zone*, *Night + restricted zone + border direction*, *Night + restricted zone + border direction + loitering*, *Object exits zone (Event resolves)*, *Same object remains in zone (Deduplication)*.
     - ANPR Pipeline: *ANPR-01 Clear plate*, *ANPR-02 No plate visible*, *ANPR-03 Blurred plate*, *ANPR-04 OCR disagreement (Temporal voting)*, *ANPR-05 Authorized vehicle*, *ANPR-06 Unknown vehicle in restricted zone*, *ANPR-07 Flagged demo plate in restricted zone*.
     - Face Pipeline: *FACE-01 Clear face*, *FACE-02 Small face*, *FACE-03 Blurred face*, *FACE-04 Dark face*, *FACE-05 Multiple frames best-selection*, *FACE-06 No face*, *FACE-07 Person never enters relevant event*.
   - **8 Camera Abstraction Validation Scenarios** (`run_camera_tests()` lines 254–324):
     - `CAMERA-01 File camera`
     - `CAMERA-02 RTSP connection attempt`
     - `CAMERA-03 Invalid RTSP URL`
     - `CAMERA-04 Camera disconnect`
     - `CAMERA-05 Camera reconnect`
     - `CAMERA-06 Multi-camera isolation`
     - `CAMERA-07 Track ID isolation`
     - `CAMERA-08 Camera health reporting`
2. **`tests/unit/test_camera.py`:**
   - Contains a single unit test `test_simulated_camera_read()`.
   - **Observed Import Defect:** Line 2 specifies `from camera.camera_source import SimulatedCamera`. The active camera implementation is in `camera.simulated_camera` (`camera/simulated_camera.py:6`).
   - **Observed Pytest Module Collision:** Running bare `pytest` produces:
     ```
     import file mismatch:
     imported module 'test_camera' has this __file__ attribute:
       C:\Users\HEMANTH\Desktop\SKYNET\scripts\test_camera.py
     which is not the same as the test file we want to collect:
       C:\Users\HEMANTH\Desktop\SKYNET\tests\unit\test_camera.py
     ```
3. **`tests/integration/` & `tests/scenarios/`:**
   - Directories exist but currently contain no test files (ready for V5 multi-camera correlation tests).
4. **Storage Governance & Audit Trail Modules:**
   - `backend/storage_manager.py:47-76` (`enforce_retention()`): Max budget 50MB, triggers at 90% utilization down to 70%, purges by tier priority (DISMISSED=0, LOW/NORMAL=1, MEDIUM=2, HIGH/CRITICAL=3), respects `is_held=True` (exempt from purge).
   - `backend/api/events_store.py:32-55` (`SQLiteEventStore`): Persistent SQLite table `audit_logs` capturing `(id, event_id, timestamp, operator, action, reason, notes)`.
   - `backend/api/events.py:34-66` and `backend/api/storage.py:34-46`: HTTP endpoints `/api/events/{id}/resolve`, `/api/events/bulk-review`, `/api/events/{id}/hold`, and `/api/audit_logs`.

### 1.3 Baseline Test Suite Execution Result
- **Executed Command:**
  ```powershell
  $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"; & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m simulator.scenarios.test_scenarios
  ```
- **Verbatim Output:**
  ```
  PS187 CORE VALIDATION

  [PASS] Normal pedestrian
  [PASS] Normal vehicle
  [PASS] Brief intrusion
  [PASS] Persistent intrusion
  [PASS] Night movement
  [PASS] Night + restricted zone
  [PASS] Night + restricted zone + border direction
  [PASS] Night + restricted zone + border direction + loitering
  [PASS] Object exits zone (Event resolves)
  [PASS] Same object remains in zone (Deduplication)
  [PASS] ANPR-01 Clear plate
  [PASS] ANPR-02 No plate visible
  [PASS] ANPR-03 Blurred plate
  [PASS] ANPR-04 OCR disagreement (Temporal voting)
  [PASS] ANPR-06 Unknown vehicle in restricted zone
  [PASS] ANPR-05 Authorized vehicle
  [PASS] ANPR-07 Flagged demo plate in restricted zone
  [PASS] FACE-01 Clear face
  [PASS] FACE-02 Small face
  [PASS] FACE-03 Blurred face
  [PASS] FACE-04 Dark face
  [PASS] FACE-05 Multiple frames best-selection
  [PASS] FACE-06 No face
  [PASS] FACE-07 Person never enters relevant event

  24/24 scenarios passed

  PS187 CAMERA ABSTRACTION VALIDATION

  [PASS] CAMERA-01 File camera
  [PASS] CAMERA-02 RTSP connection attempt
  [PASS] CAMERA-03 Invalid RTSP URL
  [PASS] CAMERA-04 Camera disconnect
  [PASS] CAMERA-05 Camera reconnect
  [PASS] CAMERA-06 Multi-camera isolation
  [PASS] CAMERA-07 Track ID isolation
  [PASS] CAMERA-08 Camera health reporting

  8/8 camera scenarios passed
  ========================================

  ALL 32 SCENARIOS PASSED
  ```
- **Exit Code:** `0` (100% pass baseline established).

---

## 2. Logic Chain

1. **Test Environment Validation (from Observation 1.1):**
   - Python 3.11.9 and all dependencies (Torch, OpenCV, Ultralytics, FastAPI, Pytest, PyYAML) are fully provisioned in `.venv`.
   - Running tests requires setting `PYTHONPATH=C:\Users\HEMANTH\Desktop\SKYNET` or using a `pytest.ini` file that declares `pythonpath = .` and `addopts = --import-mode=importlib`.
2. **Current Baseline State (from Observation 1.2 & 1.3):**
   - The single-camera intelligence engine, ANPR temporal voting, facial analysis, risk evaluation, and camera abstractions are 100% functional (32/32 tests pass).
   - `tests/unit/test_camera.py` has a legacy import (`camera.camera_source`) which should be corrected to `camera.simulated_camera` during test harness stabilization.
3. **Correlation Engine Integration Design:**
   - To satisfy Requirements R1, R2, and R3 without regressions, the new cross-camera correlation engine must operate on enriched track streams produced by camera pipelines, adhering strictly to external YAML configuration (`configs/adjacency.yaml` or `configs/correlations.yaml`).
   - Confidence scoring must output discrete categorical bands (`HIGH`, `MEDIUM`, `LOW`, or unlinked) and must never compute visual embeddings (BoT-SORT re-ID vectors) or construct N-camera graph structures.
4. **Detailed Verification Architecture (V1 - V8):**
   The verification strategy spans 8 distinct test suites to cover unit rules, boundary conditions, edge tolerances, concurrency safety, garbage collection, and end-to-end integration:

---

### Detailed Specification for Verification Plan V1–V8

#### **V1: Positive Match (Unit Test — HIGH Confidence)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v1_positive_match_high_confidence`
- **Config Under Test:**
  ```yaml
  adjacency:
    - id: "ADJ-01-02"
      source_camera: "CAM01"
      target_camera: "CAM02"
      source_exit_edge: "RIGHT"      # x >= 0.85
      target_entry_edge: "LEFT"       # x <= 0.15
      min_transit_seconds: 3.0
      max_transit_seconds: 15.0
      grace_multiplier: 1.5
      supported_classes: ["person", "car"]
  ```
- **Synthetic Input Data:**
  - Track 1 (CAM01): `track_id="CAM01-P1"`, `object_type="person"`, exit bbox `[580, 100, 620, 200]`, exit time $t_{exit} = 100.0s$.
  - Track 2 (CAM02): `track_id="CAM02-P2"`, `object_type="person"`, entry bbox `[20, 100, 60, 200]`, entry time $t_{entry} = 108.0s$ ($\Delta t = 8.0s$).
- **Assertions:**
  1. Correlation result is not `None`.
  2. `incident.status == "ACTIVE"`.
  3. `incident.linked_track_ids == ["CAM01-P1", "CAM02-P2"]`.
  4. `incident.confidence == "HIGH"` (exact string enum).
  5. `incident.object_type == "person"`.
  6. `incident.source_camera == "CAM01" and incident.target_camera == "CAM02"`.
  7. Verification confirms no appearance embedding distance was computed.

#### **V2: Class Mismatch (Unit Test — NOT Linked)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v2_class_mismatch_not_linked`
- **Synthetic Input Data:**
  - Track 1 (CAM01): `track_id="CAM01-P1"`, `object_type="person"`, exit right edge at $t = 100.0s$.
  - Track 2 (CAM02): `track_id="CAM02-V1"`, `object_type="car"`, enter left edge at $t = 108.0s$.
- **Assertions:**
  1. Correlation result is `None` (no correlation Incident formed).
  2. Correlation window for `CAM01-P1` remains in pending state awaiting a matching `"person"` detection.
  3. `CAM02-V1` track remains an independent single-camera event.
  4. Count of correlated incidents in store is `0`.

#### **V3: Timing Boundaries (Unit Test — min-0.1s, max+0.1s, min, max, grace expiry)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v3_timing_boundaries`
- **Window Definitions:** $t_{min} = 3.0s$, $t_{max} = 15.0s$, Grace upper bound $= 15.0 \times 1.5 = 22.5s$. Exit at $t_{exit} = 100.0s$.
- **Boundary Test Matrix (5 test cases):**
  | Case | Entry Timestamp | $\Delta t$ | Expected Outcome | Expected Confidence | Rationale |
  |---|---|---|---|---|---|
  | **V3.1** | $t = 102.9s$ | $2.9s$ ($min - 0.1s$) | **NOT Linked** | `None` | Physically impossible transit speed (too fast) |
  | **V3.2** | $t = 103.0s$ | $3.0s$ ($min$ exact) | **Linked** | `HIGH` | Lower boundary of core window is inclusive |
  | **V3.3** | $t = 115.0s$ | $15.0s$ ($max$ exact) | **Linked** | `HIGH` | Upper boundary of core window is inclusive |
  | **V3.4** | $t = 115.1s$ | $15.1s$ ($max + 0.1s$) | **Linked** | `LOW` | Within grace window $(15.0s < \Delta t \le 22.5s)$ |
  | **V3.5** | $t = 122.6s$ | $22.6s$ ($max \times 1.5 + 0.1s$) | **NOT Linked** | `None` | Exceeded grace window; window closed |

#### **V4: Edge Mismatch (Unit Test — Confidence Downgrade, Never HIGH)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v4_edge_mismatch_downgrade`
- **Test Scenarios:**
  1. **Source Exit Edge Mismatch:** Track exits CAM01 from TOP edge ($y \le 50$, bbox `[200, 10, 250, 50]`), enters CAM02 LEFT edge at $\Delta t = 6.0s$. Class = `"person"`.
     - *Assert:* `incident.confidence == "MEDIUM"` (downgraded from HIGH).
  2. **Target Entry Edge Mismatch:** Track exits CAM01 RIGHT edge, enters CAM02 from BOTTOM edge ($y \ge 430$, bbox `[200, 430, 250, 470]`) at $\Delta t = 6.0s$.
     - *Assert:* `incident.confidence == "MEDIUM"`.
  3. **Ambiguous / Missing Edge Vector:** Track appears in center of CAM02 without detectable boundary transition at $\Delta t = 6.0s$.
     - *Assert:* `incident.confidence == "MEDIUM"`.
  4. **Compound Mismatch (Non-configured Edge + Grace Window $\Delta t = 17.0s$):**
     - *Assert:* `incident.confidence == "LOW"`.
  5. **Invariance Assertion:** Across all mismatch permutations, assert `incident.confidence != "HIGH"`.

#### **V5: Live Two-Camera Simulator Run (Integration Test — 3 Back-to-Back Walks, Dashboard ~2s)**
- **Target Module:** `tests/integration/test_two_camera_correlation.py::test_v5_live_two_camera_walk_3x`
- **Execution Workflow:**
  1. Instantiate 2 camera pipelines with `SimulatedCamera("CAM01")` and `SimulatedCamera("CAM02")` and start the multi-camera manager.
  2. **Walk Iteration 1:**
     - Feed synthetic trajectory P1 on CAM01: moves $(x: 100 \to 620)$, exits right edge at wall-clock $T_0$.
     - At $T_0 + 4.0s$, inject trajectory P2 on CAM02: moves $(x: 20 \to 400)$ from left edge.
     - Record detection timestamp $T_{detect}$ of P2 on CAM02 and timestamp $T_{emit}$ when correlation Incident is broadcasted / received via event store or WebSocket.
     - *Assert:* $\text{Latency} = (T_{emit} - T_{detect}) \le 2.0s$.
     - *Assert:* Incident contains `linked_track_ids=["CAM01-P1", "CAM02-P2"]`, `confidence="HIGH"`.
  3. **Walk Iteration 2:**
     - Perform identical sequence for P3 on CAM01 exiting at $T_1$, P4 on CAM02 entering at $T_1 + 5.5s$.
     - *Assert:* $\text{Latency} \le 2.0s$, `confidence="HIGH"`.
  4. **Walk Iteration 3:**
     - Perform identical sequence for P5 on CAM01 exiting at $T_2$, P6 on CAM02 entering at $T_2 + 6.0s$.
     - *Assert:* $\text{Latency} \le 2.0s$, `confidence="HIGH"`.
  5. **Flakiness Check:** Assert pass count == 3/3 without test failures or restarts.

#### **V6: Concurrency & Ambiguity (Unit / Concurrency Test)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v6_concurrency_and_ambiguity`
- **Scenarios:**
  1. **Two Candidate Exits Near Exit Edge vs One Entry:**
     - CAM01: Track A exits right edge at $t = 10.0s$; Track B exits right edge at $t = 12.0s$.
     - CAM02: Track C enters left edge at $t = 17.0s$.
     - Transit times: A $\to$ C is $7.0s$; B $\to$ C is $5.0s$.
     - *Assert:* Engine links Track C to Track B (closest transit delta) or deterministic match.
     - *Assert:* Track C is **NEVER** linked twice. Exactly one Incident is emitted. Track A remains pending or expires.
  2. **One Exit vs Two Simultaneous Candidate Entries:**
     - CAM01: Track A exits at $t = 10.0s$.
     - CAM02: Track C enters at $t = 15.0s$; Track D enters at $t = 15.1s$.
     - *Assert:* Track A links to Track C. Track D remains an unlinked single-camera event. Track A is not double-linked.
  3. **Thread Safety:**
     - Execute 100 simultaneous concurrent exit and entry events across parallel worker threads.
     - *Assert:* No deadlocks, race conditions, or unhandled exceptions.

#### **V7: Cleanup & Memory Governance (Unit / Stress Test)**
- **Target Module:** `tests/unit/test_correlation_engine.py::test_v7_cleanup_expired_correlation_windows`
- **Protocol:**
  1. Initialize correlation engine with $t_{max} = 15.0s$, grace window upper bound $= 22.5s$.
  2. Inject 5,000 synthetic exit tracks on CAM01 spanning a simulated timeline from $t = 0.0s$ to $t = 3600.0s$ without injecting any CAM02 entries.
  3. Trigger garbage collection / periodic tick on correlation store at $t = 3700.0s$.
  4. *Assert:* Count of active pending correlation windows in memory == `0`.
  5. *Assert:* Memory consumption remains constant ($O(1)$ pending records after GC).

#### **V8: Regression Suite (Integration & Regression Test)**
- **Target Module:** `tests/integration/test_regression.py::test_v8_legacy_suite_unmodified`
- **Protocol:**
  1. Execute `simulator/scenarios/test_scenarios.py` with 24 core single-camera scenarios and 8 camera abstraction scenarios.
     - *Assert:* 32/32 scenarios pass.
  2. Execute Storage Governance & Audit Trail tests:
     - Verify 50MB disk quota auto-purge triggers at 90% and stops at 70%.
     - Verify tier purge hierarchy: DISMISSED (Tier 0) $\to$ ROUTINE/LOW/NORMAL (Tier 1) $\to$ CONFIRMED/MEDIUM (Tier 2) $\to$ HIGH/CRITICAL (Tier 3).
     - Verify `is_held=True` events are NEVER purged during disk cleanup.
     - Verify SQLite `audit_logs` records actions: `REVIEWED`, `REVIEWED_BULK`, `HELD`, and `SYSTEM_AUTO_PURGE`.
  3. *Assert:* 0 regressions across legacy modules.

---

## 3. Caveats

1. **Read-Only Explorer Scope:** No modifications were made to production source code during this survey phase. The legacy import error in `tests/unit/test_camera.py` was documented but intentionally not edited.
2. **Web Frontend Verification:** V5 latency requirements (~2s) should be verified both programmatically at the API/WebSocket level and visually against `dashboard/src/App.jsx`.
3. **Ultralytics YOLO Weight File:** Local model file `yolov8n.pt` (6.5MB) is present in the project root and utilized by `ByteTracker`. Unit tests for correlation logic mock detection dicts directly to execute deterministically without GPU overhead.

---

## 4. Conclusion

- The test environment in `C:\Users\HEMANTH\Desktop\SKYNET` is fully functional with Python 3.11.9 and Pytest 9.1.1.
- The baseline test suite (`simulator/scenarios/test_scenarios.py`) is 100% healthy (32/32 tests pass).
- The verification architecture for V1 through V8 is fully specified with clear input schemas, boundary matrices, timing intervals, confidence banding rules, concurrency handling, and memory GC benchmarks.
- The project is ready for the implementation and test authoring phases.

---

## 5. Verification Method

### 5.1 Baseline Test Suite Command
Run in PowerShell from the project root:
```powershell
$env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m simulator.scenarios.test_scenarios
```
*Expected Result:* Output ends with `ALL 32 SCENARIOS PASSED` and exit code `0`.

### 5.2 Verification Plan Target Commands (Upon Implementation)
1. **Pytest Unit & Concurrency Suite (V1, V2, V3, V4, V6, V7):**
   ```powershell
   $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/unit/test_correlation_engine.py -v
   ```
2. **Pytest Integration & Live Simulator Suite (V5, V8):**
   ```powershell
   $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/integration/ -v
   ```
3. **Full Combined Test Suite:**
   ```powershell
   $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m simulator.scenarios.test_scenarios
   ```
