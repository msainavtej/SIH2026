# Milestone 1 (M1) Independent Review & Adversarial Critic Report

**Milestone:** Milestone 1 — Configuration Schema, Spatial Boundary & Correlation Engine Core  
**Reviewer:** `reviewer_m1_1` (Teamwork Reviewer & Adversarial Critic)  
**Date:** 2026-08-30  
**Verdict:** **APPROVE**  
**Integrity Violations Detected:** **0 (NONE)**  

---

## 1. Observation

1. **Reviewed Source Files & Artifacts**:
   - `configs/adjacency.yaml` (39 lines): External YAML adjacency topology definition.
   - `intelligence/boundary.py` (312 lines): Spatial boundary proximity checks and directional trajectory displacement vectors.
   - `intelligence/correlation.py` (481 lines): Pydantic v2 configuration schema, `SpatialTemporalCorrelationEngine`, temporal window lifecycle, discrete confidence banding, concurrency disambiguation, and GC purging.
   - `tests/unit/test_correlation_engine.py` (417 lines): 15 comprehensive unit and boundary tests covering F1-F5, V1-V4, V6, V7.
   - `worker_m1/handoff.md`: Worker completion report.

2. **Independent Test Execution Results**:
   - Unit test suite command:
     ```powershell
     & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/unit/test_correlation_engine.py -v
     ```
     **Result**: `15 passed in 0.36s` (100% pass rate).
   - Full repository test suite command:
     ```powershell
     & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib -v
     ```
     **Result**: `118 passed, 1 warning in 14.82s` (100% pass rate across unit, integration, E2E combinatorial matrix, and platform regression suites).

3. **Integrity & Prohibition Audits**:
   - Appearance-based Re-ID embeddings (e.g. BoT-SORT, OSNet, CNN embeddings): `0` occurrences.
   - N-camera graph structures: `0` occurrences.
   - Identity overclaim strings ("confirmed person", "same person", raw float percentage scores): `0` occurrences.
   - Hardcoded / fake test bypasses: `0` occurrences. Dynamic coordinate math and timestamp comparisons verified throughout.

---

## 2. Logic Chain

1. **Requirement R1 (External Adjacency Configuration & Transit Window)**:
   - `configs/adjacency.yaml` defines `pair_id: "ADJ_CAM01_CAM02"`, `source_camera_id: "CAM01"`, `target_camera_id: "CAM02"`, `source_exit_edge: "right"`, `target_entry_edge: "left"`, `min_transit_seconds: 3.0`, `max_transit_seconds: 15.0`, and `grace_window_seconds: 7.5`.
   - `intelligence/correlation.py` validates this schema via Pydantic v2 (`AdjacencyPairConfig`, `TransitTimingConfig`, etc.), enforcing validation bounds ($t_{min} \le t_{max}$).
   - *Conclusion*: R1 is fully met and decoupled from application code.

2. **Requirement R2 & R3 (Categorical Confidence Banding & Zero Visual Embeddings)**:
   - `intelligence/boundary.py` implements pure coordinate bounding box geometry ($[x_1, y_1, x_2, y_2]$ vs. width/height margin $\delta$) and trajectory displacement vectors ($\Delta x, \Delta y$).
   - `intelligence/correlation.py` maps evaluations strictly to discrete categorical bands:
     - Core window $[3.0\text{s}, 15.0\text{s}]$ + both edges matched + confidence $\ge 0.50$ $\rightarrow$ `HIGH`
     - Core window $[3.0\text{s}, 15.0\text{s}]$ + edge ambiguous/mismatched + confidence $\ge 0.50$ $\rightarrow$ `MEDIUM`
     - Core window $[3.0\text{s}, 15.0\text{s}]$ + both edges matched + confidence $< 0.50$ $\rightarrow$ `LOW`
     - Grace window $(15.0\text{s}, 22.5\text{s}]$ + confidence $\ge 0.50$ $\rightarrow$ `LOW`
     - Timing $< 3.0\text{s}$ or $> 22.5\text{s}$ or below threshold $\rightarrow$ `None` (no correlation created).
   - No continuous float scores or identity overclaims are emitted.
   - *Conclusion*: R2 and R3 are strictly satisfied.

3. **Concurrency Disambiguation & Memory Bounding (Rules V6, V7)**:
   - Concurrency (V6): Candidate windows are ranked by closeness to expected transit time ($|\Delta t - t_{expected}|$). When candidates tie within the configurable `ambiguity_tie_threshold_s` ($0.5\text{s}$), the engine declines correlation (`None`), avoiding arbitrary guessing. 1-to-1 matching invariant prevents double-linking consumed windows.
   - Thread safety: `threading.RLock()` protects window state transitions during concurrent calls.
   - Memory bounding (V7): `cleanup_expired` purges expired/consumed windows older than $t_{max} + t_{grace}$ ($22.5\text{s}$). The circuit breaker `max_active_windows` prevents unbounded memory growth under synthetic burst loads.
   - *Conclusion*: V6 and V7 are robustly verified.

---

## 3. Adversarial & Edge Case Stress-Testing

| Scenario | Tested Invariant | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| **Timing Boundary: 2.9s** | $t < t_{min}$ | Link declined (`None`) | `None` returned | **PASS** |
| **Timing Boundary: 3.0s** | $t = t_{min}$ | Linked `HIGH` | `HIGH` returned | **PASS** |
| **Timing Boundary: 15.0s** | $t = t_{max}$ | Linked `HIGH` | `HIGH` returned | **PASS** |
| **Timing Boundary: 15.1s** | $t > t_{max}$ in grace | Linked `LOW` | `LOW` returned | **PASS** |
| **Timing Boundary: 22.5s** | $t = t_{max} + t_{grace}$ | Linked `LOW` | `LOW` returned | **PASS** |
| **Timing Boundary: 22.6s** | $t > t_{max} + t_{grace}$ | Link declined (`None`) | `None` returned | **PASS** |
| **Edge Mismatch: Top Exit** | Non-configured exit edge | Downgraded to `MEDIUM`, never `HIGH` | `MEDIUM` returned | **PASS** |
| **Edge Mismatch: Bottom Entry** | Non-configured entry edge | Downgraded to `MEDIUM`, never `HIGH` | `MEDIUM` returned | **PASS** |
| **Ambiguous Candidate Tie** | Multiple exits at same $t$ ($\Delta \le 0.5\text{s}$) | Link declined rather than guess | `None` returned | **PASS** |
| **Concurrent Execution** | 100 parallel worker threads | No race conditions / deadlocks | 0 exceptions | **PASS** |
| **Extended Unmatched Exits** | 5,000 synthetic exit bursts | GC purges expired windows | 5,000 purged, 0 active | **PASS** |

---

## 4. Review Findings

### Minor Findings (Non-Blocking Quality Suggestions)

1. **Minor Finding 1 — Fallback Default in `evaluate_correlation`**:
   - **Location**: `intelligence/correlation.py:360`
   - **Observation**: `class_match = (window.object_type == entry_track.get("object_type"))` compares against `entry_track.get("object_type")` (which returns `None` if the key is absent), whereas `on_track_entry` (line 283) uses `track.get("object_type", "unknown")`.
   - **Assessment**: While all upstream callers (`CameraManager`, `YOLO`) always supply `"object_type"`, using `entry_track.get("object_type", "unknown")` would ensure 100% defensive consistency against malformed payloads.
   - **Action**: Recommended for minor cleanup during M2/M3 refactorings; non-blocking.

2. **Minor Finding 2 — Pydantic V2 Migration Warning in `backend/schemas/events.py`**:
   - **Location**: `backend/schemas/events.py:11`
   - **Observation**: `PydanticDeprecatedSince20: Support for class-based config is deprecated, use ConfigDict instead.`
   - **Assessment**: Pre-existing model warning in M2 scope.
   - **Action**: Worker on Milestone 2 can modernize `class Config:` to `model_config = ConfigDict(...)`.

---

## 5. Caveats

- Milestone 1 scope covers core boundary analysis, correlation engine logic, and unit verification. Multi-camera live RTSP streams and dashboard UI visual elements are owned by Milestones 2 and 3.

---

## 6. Conclusion & Verdict

**Final Verdict:** **`APPROVE`**

Milestone 1 satisfies all requirements set forth in `ORIGINAL_REQUEST.md` and `PROJECT.md`. The implementation exhibits high architectural fidelity, clean separation of concerns, comprehensive test coverage (15/15 unit tests, 118/118 overall test suite pass), zero appearance-based embedding dependencies, and strict compliance with anti-overclaim requirements.

---

## 7. Verification Method

To independently reproduce and verify this review verdict:

```powershell
# 1. Run M1 Unit & Boundary Verification Suite
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/unit/test_correlation_engine.py -v

# 2. Run Full Regression & E2E Test Suite
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib -v
```
