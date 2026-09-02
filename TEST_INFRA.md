# SKYNET Cross-Camera Spatial-Temporal Correlation Engine: Test Infrastructure & Architecture

**Document Version:** 1.0.0  
**Project:** SIH PS187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance  
**Author:** `test_writer_e2e`  
**Date:** 2026-08-30  
**Target Module:** Cross-Camera Spatial-Temporal Correlation Engine  

---

## 1. Test Architecture & Runner Specification

### 1.1 Environment & Test Runner
- **Test Runner:** `pytest` (v9.1.1)
- **Python Runtime:** Python 3.11.9 (`C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe`)
- **Execution Mode:** `--import-mode=importlib` with `pythonpath = .` defined in `pytest.ini`.
- **Target Directories:**
  - `tests/unit/` — Unit tests for configuration, spatial boundary math, temporal lifecycle, and confidence banding.
  - `tests/integration/` — Integration tests for 2-camera pipeline, live walk simulator, and regression baseline.
  - `tests/e2e/` — End-to-end incident workflows, anti-overclaim compliance, and pairwise scenario matrices.

### 1.2 Global Configuration (`pytest.ini`)
```ini
[pytest]
pythonpath = .
testpaths = tests
addopts = --import-mode=importlib -v
```

### 1.3 Execution Commands
```powershell
# Run the entire test suite
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/

# Run specific tiers / modules
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/unit/test_correlation_engine.py
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/integration/test_two_camera_correlation.py
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/integration/test_regression.py
& "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/e2e/test_e2e_correlation.py
```

---

## 2. 4-Tier Test Suite Structure

The test harness is organized into four distinct tiers to provide hierarchical verification across isolated logic, boundary stress, combinatorial permutations, and end-to-end system operations.

```
+-----------------------------------------------------------------------------------+
|                           4-TIER TEST SUITE STRUCTURE                             |
+-----------------------------------------------------------------------------------+

  [ Tier 1: Feature Coverage ]
  ├── Configuration Schema & Validation (configs/adjacency.yaml, Pydantic models)
  ├── Spatial Boundary & Directional Velocity Analyzer (Edge math, entry/exit detection)
  ├── Correlation Window Lifecycle (OPEN, CONSUMED, EXPIRED state transitions)
  └── Single-Camera Pipeline Regression (24 core scenarios + 8 camera abstraction tests)

  [ Tier 2: Boundary & Corner Conditions ]
  ├── V3 Timing Boundaries (2.9s [min-0.1s], 3.0s [min], 15.0s [max], 15.1s [grace], 22.6s [expired])
  ├── V4 Edge Mismatches (Top exit, Bottom entry, Center apparition, Compound grace downgrade)
  ├── Detection Confidence Thresholding (<0.50 confidence yields LOW band)
  ├── V6 Concurrency & Ambiguity (Closer time delta selection, tie-breaking link declination)
  └── V7 Garbage Collection Stress (5,000 synthetic exits purged; memory bounded)

  [ Tier 3: Pairwise Combinations Matrix ]
  ├── (Class Match vs Mismatch) x (Edge Match vs Mismatch) x (Core vs Grace vs Expired Timing)
  ├── Multi-Class Grid (person, car, truck, bus, unknown)
  └── Disambiguation Combinations (1-to-1, 1-to-many, many-to-1, many-to-many)

  [ Tier 4: Real-World Scenarios & E2E Workflows ]
  ├── V5 Live 2-Camera Simulated Walk (3x back-to-back runs, latency <= 2.0s, HIGH confidence)
  ├── Operator Lifecycle & Hold Governance (Correlated Incident Hold -> storage purge exemption)
  ├── Operator Incident Dismissal & Physical Evidence Cleanup (Audit trail logging)
  ├── 50MB Storage Budget Auto-Purge (90% trigger down to 70% target, tier hierarchy)
  └── Anti-Overclaim Forensic Audit (Zero "confirmed person" / "same person" phrasing)
```

---

## 3. Feature Inventory & Verification Coverage Matrix

| Feature ID | Feature Name | Milestone | Verification Target | Test Module & Function | Tier |
|---|---|---|---|---|---|
| **F1** | External Adjacency Configuration | M1 | Schema validation, YAML loading, default fallback | `tests/unit/test_correlation_engine.py::test_f1_adjacency_config_loading` | Tier 1 |
| **F2** | Spatial Edge Boundary & Velocity Analyzer | M1 | Right exit ($x \ge 0.9W$), Left entry ($x \le 0.1W$), directional vectors | `tests/unit/test_correlation_engine.py::test_f2_spatial_boundary_math` | Tier 1 |
| **F3** | Correlation Window Lifecycle Core | M1 | Window creation, state progression (OPEN &rarr; CONSUMED/EXPIRED) | `tests/unit/test_correlation_engine.py::test_f3_window_lifecycle_transitions` | Tier 1 |
| **F4** | Categorical Confidence Banding | M1 | Discrete bands (HIGH, MEDIUM, LOW, NONE), zero percentages | `tests/unit/test_correlation_engine.py::test_f4_confidence_band_matrix` | Tier 1 |
| **F5** | Concurrency & Disambiguation Protocol | M1 | 1-to-1 matching, closest $| \Delta t - t_{expected} |$, tie declination | `tests/unit/test_correlation_engine.py::test_v6_concurrency_and_disambiguation` | Tier 2 |
| **F6** | Multi-Camera Pipeline Integration | M2 | CameraManager routing, isolated track IDs (`CAM01-P1`), SQLiteEventStore | `tests/integration/test_two_camera_correlation.py::test_f6_camera_manager_linkage` | Tier 4 |
| **F7** | Storage Governance & Audit Trail Parity | M2 | 50MB auto-purge, 3-tier retention, `is_held=True` protection, audit logs | `tests/integration/test_regression.py::test_f7_storage_governance_and_audit_trail` | Tier 2/4 |
| **F8** | Live 2-Camera Simulator Scenario | M3 | 3x back-to-back walk simulations, latency $\le 2.0s$, dashboard badge | `tests/integration/test_two_camera_correlation.py::test_v5_live_two_camera_walk_3x` | Tier 4 |
| **F9** | Dashboard UI & Anti-Overclaim Compliance | M3 | Visible badges, zero forbidden phrases ("confirmed identity", "same person") | `tests/e2e/test_e2e_correlation.py::test_f9_anti_overclaim_compliance` | Tier 4 |
| **F10** | E2E Incident Workflows & Combinatorial Matrix | M4 | Full lifecycle traversal, operator review, dismissal, storage purge | `tests/e2e/test_e2e_correlation.py::test_f10_e2e_incident_lifecycle` | Tier 3/4 |
| **V1** | Unit — Positive Match (HIGH Confidence) | M1 | Class match + mapped edges + core window (3-15s) &rarr; HIGH | `tests/unit/test_correlation_engine.py::test_v1_positive_match_high_confidence` | Tier 1 |
| **V2** | Unit — Class Mismatch (NOT Linked) | M1 | `person` exit CAM01 vs `car` entry CAM02 &rarr; NONE | `tests/unit/test_correlation_engine.py::test_v2_class_mismatch_not_linked` | Tier 1 |
| **V3** | Unit — Timing Boundaries | M1 | $2.9s \to \text{NONE}$, $3.0s \to \text{HIGH}$, $15.0s \to \text{HIGH}$, $15.1s \to \text{LOW}$, $22.6s \to \text{NONE}$ | `tests/unit/test_correlation_engine.py::test_v3_timing_boundaries` | Tier 2 |
| **V4** | Unit — Edge Mismatches & Downgrades | M1 | Top exit, bottom entry, center entry, non-configured + grace &rarr; MEDIUM/LOW | `tests/unit/test_correlation_engine.py::test_v4_edge_mismatch_downgrade` | Tier 2 |
| **V5** | Integration — Live 2-Camera Simulated Walk | M3 | 3x consecutive walk runs with latency $\le 2.0s$ | `tests/integration/test_two_camera_correlation.py::test_v5_live_two_camera_walk_3x` | Tier 4 |
| **V6** | Unit/Concurrency — Multi-Track Disambiguation | M1 | Closer time delta selection, tie declination, 100-thread stress test | `tests/unit/test_correlation_engine.py::test_v6_concurrency_and_disambiguation` | Tier 2 |
| **V7** | Unit/Stress — Unmatched Exit GC Cleanup | M1 | 5,000 synthetic exits with no entries &rarr; zero memory leak after GC | `tests/unit/test_correlation_engine.py::test_v7_cleanup_expired_correlation_windows` | Tier 2 |
| **V8** | Regression — Full Baseline & Storage Parity | M2 | 32/32 baseline scenarios pass, 50MB storage auto-purge, SQLite audit logs | `tests/integration/test_regression.py::test_v8_legacy_suite_unmodified` | Tier 1/2 |

---

## 4. Test Case Derivation & Authoritative Sources

Every test case derives its expected values from the project specifications:
1. **Rule R1 & V1/V2**: `ORIGINAL_REQUEST.md:18-20, 34-37` and `PROJECT.md:18-30` &rarr; Expected: 2-camera pair link, class match filter.
2. **Rule R2 & V3/V4**: `ORIGINAL_REQUEST.md:22-28, 38-41` and `explorer_survey_spec/handoff.md:74-87` &rarr; Expected: Confidence decision table (`HIGH`, `MEDIUM`, `LOW`, `NONE`).
3. **Rule R3 & F9**: `ORIGINAL_REQUEST.md:29-31, 56-57` &rarr; Expected: No BoT-SORT/ResNet imports, no "same person" / "confirmed identity" text.
4. **Rule V5**: `ORIGINAL_REQUEST.md:42-43` &rarr; Expected: 3x consecutive simulated walks, latency $\le 2.0s$.
5. **Rule V6**: `ORIGINAL_REQUEST.md:44-45` &rarr; Expected: 1-to-1 matching invariant, closest time delta, tie declination within $\epsilon = 0.5s$.
6. **Rule V7**: `ORIGINAL_REQUEST.md:46-47` &rarr; Expected: Eviction of windows after $t_{exit} + t_{max} + t_{grace} = 22.5s$.
7. **Rule V8**: `ORIGINAL_REQUEST.md:48-49` &rarr; Expected: 32/32 existing scenarios in `simulator/scenarios/test_scenarios.py` pass without regression.

---

## 5. Adversarial & Edge Case Invariants

The test suite enforces the following critical invariants:
1. **Strict Re-ID Prohibition Invariant:** Under no condition does the engine invoke appearance embeddings or feature distance metrics.
2. **Confidence Downgrade Monotonicity Invariant:** Degraded edge match or grace window timing must NEVER upgrade confidence to `HIGH`.
3. **1-to-1 Linkage Invariant:** An exiting track $\mathcal{T}_{src}$ can link to at most one entering track $\mathcal{T}_{tgt}$, and vice versa.
4. **Tie Declination Invariant:** When two candidate exits have identical transit deltas (within 0.5s), the engine safely declines to link rather than making a random or arbitrary assignment.
5. **Bounded Memory Invariant:** Unmatched exits must be deterministically garbage-collected, maintaining $O(k)$ memory where $k = \text{rate} \times (t_{max} + t_{grace})$.
