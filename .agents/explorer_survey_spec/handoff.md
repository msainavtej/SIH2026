# Cross-Camera Spatial-Temporal Correlation Engine Specification

**Document Version:** 1.0.0  
**Project:** SIH PS187 — AI-Based Intelligent Video Analytics Platform for Border Surveillance  
**Author:** `explorer_survey_spec` (Specification Miner)  
**Date:** 2026-08-30  
**Target Module:** Cross-Camera Spatial-Temporal Correlation Engine (`intelligence/correlation_engine.py`, `backend/schemas/events.py`, `configs/adjacency.yaml`)

---

## 1. Executive Summary

This specification formalizes the requirements, architecture, configuration schemas, mathematical boundary rules, confidence banding matrices, concurrency resolution heuristics, lifecycle management, and storage governance integrations for a **cross-camera spatial-temporal correlation engine linking exactly two adjacent cameras** (`CAM01` and `CAM02`).

The system links track segments across cameras purely through **calibrated adjacency mapping, transit time windows, object classification consistency, and spatial entry/exit bounding box vectors**, with **zero reliance on appearance-based Re-ID embeddings** (e.g. BoT-SORT visual features, CNN embeddings) and **zero N-camera graph complexity**. All correlation confidence outputs are strictly categorized into discrete confidence bands (`HIGH`, `MEDIUM`, `LOW`, `NONE`) with explicit safeguards against overclaiming identity matches.

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Correlation | Single-Pair Adjacency Mapping | Defines directional spatial linkage from Source Camera (CAM-01) to Target Camera (CAM-02) with configured exit/entry boundaries and transit time bounds. | `source_camera_id`, `target_camera_id`, `source_exit_edge`, `target_entry_edge`, `min_transit_s`, `max_transit_s`, `grace_s` | `AdjacencyConfig` model instance | Rejects invalid edges or inverted time ranges ($t_{min} > t_{max}$) with validation error. | `ORIGINAL_REQUEST.md:18-20`, `configs/` |
| 2 | Correlation | Correlation Window Lifecycle | When a track exits the source camera's configured edge, an active temporal window is opened. | `track_id`, `camera_id`, `object_type`, `exit_time`, `exit_bbox`, `exit_velocity` | `CorrelationWindow` object (State: `OPEN`) | Tracks exiting non-mapped edges open un-flagged windows or are ignored per policy. | `ORIGINAL_REQUEST.md:19, 46-47` |
| 3 | Correlation | Object Class Matching | Evaluates class compatibility between the exiting track and candidate entering tracks (e.g., `person` $\leftrightarrow$ `person`, `car` $\leftrightarrow$ `car`). | `source_class`, `target_class` | Boolean `is_class_compatible` | Class mismatch results in immediate decline to link (`NONE`). | `ORIGINAL_REQUEST.md:19, 36-37` |
| 4 | Correlation | Spatial Edge Verification | Checks if a track's bounding box and trajectory vector match configured exit/entry boundaries. | `bbox [x1, y1, x2, y2]`, `trajectory [[x,y]...]`, `frame_size (W,H)`, `configured_edge` | `EdgeMatchResult(matched: bool, confidence_modifier: float)` | Ambiguous or non-matching edges downgrade confidence band from HIGH to MEDIUM. | `ORIGINAL_REQUEST.md:24-26, 40-41` |
| 5 | Correlation | Transit Timing Evaluation | Calculates $\Delta t = t_{entry} - t_{exit}$ and compares against core window $[t_{min}, t_{max}]$ and grace window $(t_{max}, t_{max} + t_{grace}]$. | `exit_timestamp`, `entry_timestamp`, `transit_config` | `TimingBand` (`CORE_WINDOW`, `GRACE_WINDOW`, `TOO_FAST`, `EXPIRED`) | $\Delta t < t_{min}$ or $\Delta t > t_{max} + t_{grace}$ yields no correlation. | `ORIGINAL_REQUEST.md:24-27, 38-39` |
| 6 | Correlation | Categorical Confidence Banding | Assigns discrete confidence bands (`HIGH`, `MEDIUM`, `LOW`, `NONE`) based on class match, edge fidelity, timing, and detection quality. | Evaluation context (`class_match`, `edge_match`, `timing_band`, `det_conf`) | `ConfidenceBand` enum (`HIGH`, `MEDIUM`, `LOW`, `NONE`) | Returns `NONE` if below low threshold; no Incident created. | `ORIGINAL_REQUEST.md:22-28` |
| 7 | Correlation | Unified Incident Creation | Bundles linked source event/track and target event/track into a single correlated Incident entity with explicit metadata. | Source track data, Target track data, Confidence Band, Timing stats | `IncidentSchema` / `EventSchema` with cross-camera linkage | Emits standalone unlinked events if correlation fails. | `ORIGINAL_REQUEST.md:19, 34-35`, `backend/schemas/events.py` |
| 8 | Correlation | Concurrency & Multi-Track Disambiguation | Resolves simultaneous candidate tracks at exit or entry using deterministic time-closeness heuristics or declines link if ambiguous. | Multiple candidate `CorrelationWindow` or entry track candidates | Selected 1-to-1 match or `DECLINED` | When multiple candidates tie within ambiguity delta, link is declined rather than guessed. | `ORIGINAL_REQUEST.md:44-45` |
| 9 | Memory / Lifecycle | Correlation Window Garbage Collection | Deterministically evicts and frees expired correlation windows after $t_{exit} + t_{max} + t_{grace}$. | Current timestamp $t_{now}$, active correlation windows map | Pruned windows, reclaimed memory | Runs every frame / cleanup tick; prevents unbounded memory growth. | `ORIGINAL_REQUEST.md:46-47` |
| 10 | Security / Compliance | Anti-Overclaim Governance | Enforces UI, API, and log terminology rules forbidding "confirmed identity" or "same person" claims. | Incident presentation and log formatters | Compliant labels: "Correlated Track Link [HIGH]" | Fails build / lint if prohibited terms ("same person", "confirmed identity") appear in UI/logs. | `ORIGINAL_REQUEST.md:23, 29-31, 56-57` |
| 11 | Storage / Governance | Correlated Evidence Retention | Integrates correlated Incidents into the SQLite store and 3-tier storage governor (Routine, Confirmed, Held) with immutable audit logging. | `IncidentSchema`, `SQLiteEventStore`, `StorageManager` | Multi-camera evidence retention & audit log | Respects operator `HOLD`, auto-purges routine tiers at 90% disk capacity, logs audit trail. | `ORIGINAL_REQUEST.md:59`, `backend/storage_manager.py`, `backend/api/events_store.py` |

---

## 3. Edge Cases Matrix

| # | Feature | Scenario / Input | Expected System Behavior | Rationale / Rule Reference |
|---|---|---|---|---|
| E1 | Transit Timing | Entry at $t_{entry} = t_{exit} + t_{min} - 0.1\text{s}$ (e.g. 2.9s when $t_{min}=3.0\text{s}$) | **NO correlation created (`NONE`)**. Tracks remain independent events. | Below minimum transit time boundary (physically implausible travel speed). Rule V3. |
| E2 | Transit Timing | Entry exactly at $t_{entry} = t_{exit} + t_{min}$ (e.g. 3.0s) | **Correlated (`HIGH` if edges match)**. Unified Incident emitted. | Inclusive lower boundary of core transit window. Rule V3. |
| E3 | Transit Timing | Entry exactly at $t_{entry} = t_{exit} + t_{max}$ (e.g. 15.0s) | **Correlated (`HIGH` if edges match)**. Unified Incident emitted. | Inclusive upper boundary of core transit window. Rule V3. |
| E4 | Transit Timing | Entry at $t_{entry} = t_{exit} + t_{max} + 0.1\text{s}$ (e.g. 15.1s) | **Correlated with `LOW` confidence**. Unified Incident emitted. | Within grace window $(t_{max}, t_{max} + t_{grace}]$. Rule R2, V3. |
| E5 | Transit Timing | Entry at $t_{entry} = t_{exit} + t_{max} + t_{grace} + 0.1\text{s}$ (e.g. 22.6s when grace is +50% = 7.5s) | **NO correlation created (`NONE`)**. Window already garbage collected. | Grace window expired; correlation window pruned. Rule V3, V7. |
| E6 | Class Matching | `person` exits CAM-01 at $t=0$, `car` enters CAM-02 at $t=5.0\text{s}$ | **NO correlation created (`NONE`)**. Tracks remain independent. | Object class mismatch. Rule R2, V2. |
| E7 | Class Matching | `truck` exits CAM-01, `bus` enters CAM-02 | **NO correlation (`NONE`)** unless vehicle superclass matching is explicitly configured. | Strict class equality is safe default. Rule R2. |
| E8 | Spatial Edge | Track exits CAM-01 through **top** edge, enters CAM-02 through **left** edge at $t=5.0\text{s}$ | **Correlated with `MEDIUM` confidence** (never upgrades to HIGH). | Non-configured exit edge violates spatial directional expectation; downgrades band. Rule R2, V4. |
| E9 | Spatial Edge | Track exits CAM-01 right edge, enters CAM-02 from **center** (appears mid-frame) at $t=5.0\text{s}$ | **Correlated with `MEDIUM` confidence**. | Ambiguous entry edge. Rule R2, V4. |
| E10 | Detection Quality | Exact class match + correct edges + core timing, but CAM-02 YOLO detection confidence is 0.42 ($< 0.50$ threshold) | **Correlated with `LOW` confidence**. | Borderline detection confidence prevents HIGH classification. Rule R2. |
| E11 | Concurrency | Two identical class tracks ($T_A, T_B$) exit CAM-01 at $t=0$ and $t=0.5\text{s}$. One track $T_C$ enters CAM-02 at $t=9.0\text{s}$. | System links $T_A$ or $T_B$ based on closest $| \Delta t - t_{expected} |$. Window for linked track is CONSUMED. The remaining window stays OPEN until match or expiry. | 1-to-1 matching invariant; prevents double-linking one exit to multiple entries. Rule R1, V6. |
| E12 | Concurrency | Two exiting tracks $T_A, T_B$ exit simultaneously ($t_A = t_B$) with identical classes/edges. Single entry $T_C$ appears at $t=9.0\text{s}$. | System detects exact ambiguity tie ($|\Delta t_A - \Delta t_B| < \epsilon_{tie}$), **DECLINES TO LINK**, and logs disambiguation skip. | Avoids arbitrary guessing when candidates are equidistant. Rule V6. |
| E13 | Concurrency | Single exit $T_A$ at $t=0$. Two entries $T_C$ (at $t=6.0\text{s}$) and $T_D$ (at $t=7.0\text{s}$) appear on CAM-02. | $T_C$ links to $T_A$ at $t=6.0\text{s}$. Window is closed. When $T_D$ arrives at $t=7.0\text{s}$, no open window exists, so $T_D$ remains an unlinked independent event. | First valid arrival consumes window; prevents 1-to-many over-linking. Rule V6. |
| E14 | Memory / GC | 1,000 synthetic tracks exit CAM-01 over 1 hour with zero detections on CAM-02. | All 1,000 windows transition from `OPEN` to `EXPIRED` and are purged. Active window count stays $\le \text{rate} \times (t_{max} + t_{grace})$. Peak memory is strictly bounded. | Garbage collection enforces zero unbounded memory growth. Rule V7. |
| E15 | Storage & Audit | Correlated Incident with HIGH confidence and HIGH risk is marked `DISMISSED` by operator. | Both CAM-01 and CAM-02 mock evidence MP4 files are physically deleted. Permanent audit record written to `audit_logs` table. | Storage governance & audit trail parity. Rule Acceptance Criteria, V8. |

---

## 4. Formalized Requirements Specification

### R1. Adjacency Mapping and Transit Logic
1. **Topology Definition**: Exactly one adjacency pair is defined between two distinct camera IDs:
   $$\text{Adjacency}: \text{Source Camera } (\mathcal{C}_{src}) \xrightarrow{\quad\Delta t \in [t_{min}, t_{max}]\quad} \text{Target Camera } (\mathcal{C}_{tgt})$$
2. **External Configuration**: The configuration must reside in an external YAML file (e.g. `configs/adjacency.yaml`), loaded dynamically at engine initialization without hardcoded constants in Python logic.
3. **Correlation Window Triggering**:
   - When a track $\mathcal{T}_{src}$ on $\mathcal{C}_{src}$ terminates or crosses the exit spatial threshold $\mathcal{E}_{exit}$ at timestamp $t_{exit}$, a `CorrelationWindow` instance $\mathcal{W}$ is instantiated:
     $$\mathcal{W} = \langle \text{id}=\text{UUID}, \mathcal{C}_{src}, \text{track\_id}=\mathcal{T}_{src}.\text{id}, \text{class}=\mathcal{T}_{src}.\text{type}, t_{exit}, \text{edge\_valid}=\text{bool}, \text{status}=\text{OPEN} \rangle$$
4. **Candidate Matching**:
   - When a new track $\mathcal{T}_{tgt}$ is initialized on $\mathcal{C}_{tgt}$ at timestamp $t_{entry}$ within entry region $\mathcal{E}_{entry}$:
     - If $\mathcal{T}_{tgt}.\text{type} == \mathcal{W}.\text{class}$ and $t_{min} \le (t_{entry} - t_{exit}) \le t_{max} + t_{grace}$:
       - A unified `Incident` $\mathcal{I}$ is generated linking $\mathcal{T}_{src}$ and $\mathcal{T}_{tgt}$.
       - $\mathcal{W}$ transitions to state `CONSUMED`.

### R2. Confidence Banding Rules & Decision Table
1. **No Raw Percentages or False Identity Claims**: The engine must emit categorical bands: `HIGH`, `MEDIUM`, `LOW`, or `NONE`.
2. **Confidence Band Evaluation Logic**:

$$\text{ConfidenceBand} = \begin{cases}
\mathbf{HIGH} & \text{if } \text{ClassMatch} \land \text{BothEdgesMatched} \land (t_{min} \le \Delta t \le t_{max}) \land (\text{Conf} \ge \theta_{det}) \\
\mathbf{MEDIUM} & \text{if } \text{ClassMatch} \land \neg\text{BothEdgesMatched} \land (t_{min} \le \Delta t \le t_{max}) \land (\text{Conf} \ge \theta_{det}) \\
\mathbf{LOW} & \text{if } \text{ClassMatch} \land (t_{max} < \Delta t \le t_{max} + t_{grace}) \land (\text{Conf} \ge \theta_{det}) \\
\mathbf{LOW} & \text{if } \text{ClassMatch} \land \text{BothEdgesMatched} \land (t_{min} \le \Delta t \le t_{max}) \land (\text{Conf} < \theta_{det}) \\
\mathbf{NONE} & \text{otherwise (e.g. class mismatch, } \Delta t < t_{min}, \Delta t > t_{max} + t_{grace})
\end{cases}$$

3. **Safe Default**: If confidence is below `LOW`, NO correlation is created. Two independent, unlinked events are retained.

### R3. Strict Prohibitions (No Appearance Re-ID & No N-Camera Graph Logic)
1. **No Appearance Embeddings**: Feature extractors (e.g. BoT-SORT CNN embeddings, DeepSORT Re-ID embeddings, ResNet, OSNet) are strictly forbidden.
2. **No N-Camera Graph Solvers**: Multi-camera graph matching, global Hungarian clustering across arbitrary camera topologies, or hypergraph state estimations are strictly forbidden.
3. **No Biometric / Identity Terminology**: UI strings, logs, and API schemas must NEVER use terms such as `"confirmed person"`, `"same person"`, `"identity match"`, or `"100% matched subject"`.

---

## 5. Verification Requirements (V1 - V8)

| Code | Type | Title | Verification Criteria | Expected Outcome |
|---|---|---|---|---|
| **V1** | Unit | Positive Match | Synthetic fixture: `CAM-01` track exits right edge at $t=0$; same-class track enters `CAM-02` left edge at $t=5.0\text{s}$ ($t \in [3\text{s}, 15\text{s}]$). | Assert unified Incident created, links `track_id_1` and `track_id_2`, `confidence == "HIGH"`. |
| **V2** | Unit | Class Mismatch | Synthetic fixture: `person` exits `CAM-01` at $t=0$; `car` enters `CAM-02` at $t=5.0\text{s}$. | Assert NOT linked. No Incident created. Two independent single-camera events. |
| **V3** | Unit | Timing Boundaries | Test entry timestamps: (1) $t=2.9\text{s}$ ($\Delta t < 3.0\text{s}$); (2) $t=3.0\text{s}$ (lower bound); (3) $t=15.0\text{s}$ (upper bound); (4) $t=15.1\text{s}$ (grace); (5) $t=22.6\text{s}$ (expired). | (1) `NONE`; (2) `HIGH`; (3) `HIGH`; (4) `LOW`; (5) `NONE`. |
| **V4** | Unit | Edge Mismatch | Track exits `CAM-01` top edge instead of configured right edge; enters `CAM-02` left edge at $t=5.0\text{s}$. | Assert confidence band downgrades to `MEDIUM`, NEVER upgrades to `HIGH`. |
| **V5** | Integration | Live 2-Camera Simulator | Simulated object walks across `CAM-01` right edge into `CAM-02` left edge in live pipeline. | Dashboard / API reflects correlated Incident with visible confidence badge within $\le 2\text{s}$ of entry. Must pass 3 back-to-back runs. |
| **V6** | Unit / Int | Concurrency / Multi-Track | Two tracks exit `CAM-01` within 0.5s; single track enters `CAM-02`. | No system crash, no double-linking (1-to-1 only). Picks closest time match or safely declines if ambiguous. |
| **V7** | Unit / Stress | Lifecycle & GC Cleanup | Inject 1,000 synthetic exits with no corresponding entries on `CAM-02`. | Verify all expired windows are purged after $t_{max} + t_{grace}$. Memory stays $O(k)$ bounded with zero leaks. |
| **V8** | Regression | Full Test Suite | Run existing test suite (`pytest`, camera tests, storage governance, ANPR voting, Face quality, audit logs). | 100% existing test pass rate with zero regressions. |

---

## 6. Detailed Architectural Specification

### 6.1 Adjacency Configuration Schema

#### File: `configs/adjacency.yaml`
```yaml
# Cross-Camera Adjacency and Transit Mapping Configuration
adjacency_map:
  pair_id: "ADJ_CAM01_CAM02"
  enabled: true
  source_camera_id: "CAM01"
  target_camera_id: "CAM02"
  
  # Spatial boundary edge definitions
  spatial_edges:
    source_exit_edge: "right"        # Options: left, right, top, bottom
    target_entry_edge: "left"        # Options: left, right, top, bottom
    edge_threshold_fraction: 0.10    # 10% of frame boundary (e.g. x >= 0.90*W for right edge)
    min_trajectory_points: 3         # Minimum historical points to compute directional vector
    
  # Temporal transit parameters (in seconds)
  transit_timing:
    min_transit_seconds: 3.0
    max_transit_seconds: 15.0
    grace_window_seconds: 7.5        # +50% beyond max_transit (allows up to 22.5s)
    ambiguity_tie_threshold_s: 0.5   # If two exits differ by < 0.5s from target, decline link
    
  # Confidence evaluation thresholds
  confidence_rules:
    detection_conf_threshold: 0.50   # YOLO detection confidence threshold
    allow_ambiguous_edge_medium: true
    allow_grace_window_low: true
    expected_transit_seconds: 9.0    # (min + max) / 2 for time-closeness heuristic
    
  # Cleanup and GC parameters
  lifecycle:
    gc_interval_seconds: 1.0         # How often expired windows are purged
    max_active_windows: 200          # Circuit breaker cap
```

#### Pydantic Model Schema:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class SpatialEdgesConfig(BaseModel):
    source_exit_edge: Literal["left", "right", "top", "bottom"] = "right"
    target_entry_edge: Literal["left", "right", "top", "bottom"] = "left"
    edge_threshold_fraction: float = Field(default=0.10, ge=0.01, le=0.30)
    min_trajectory_points: int = Field(default=3, ge=1)

class TransitTimingConfig(BaseModel):
    min_transit_seconds: float = Field(default=3.0, ge=0.1)
    max_transit_seconds: float = Field(default=15.0, ge=1.0)
    grace_window_seconds: float = Field(default=7.5, ge=0.0)
    ambiguity_tie_threshold_s: float = Field(default=0.5, ge=0.0)
    expected_transit_seconds: Optional[float] = None

    def get_expected_transit(self) -> float:
        if self.expected_transit_seconds is not None:
            return self.expected_transit_seconds
        return (self.min_transit_seconds + self.max_transit_seconds) / 2.0

class ConfidenceRulesConfig(BaseModel):
    detection_conf_threshold: float = Field(default=0.50, ge=0.1, le=1.0)
    allow_ambiguous_edge_medium: bool = True
    allow_grace_window_low: bool = True

class LifecycleConfig(BaseModel):
    gc_interval_seconds: float = Field(default=1.0, ge=0.1)
    max_active_windows: int = Field(default=200, ge=10)

class AdjacencyPairConfig(BaseModel):
    pair_id: str
    enabled: bool = True
    source_camera_id: str
    target_camera_id: str
    spatial_edges: SpatialEdgesConfig = Field(default_factory=SpatialEdgesConfig)
    transit_timing: TransitTimingConfig = Field(default_factory=TransitTimingConfig)
    confidence_rules: ConfidenceRulesConfig = Field(default_factory=ConfidenceRulesConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
```

---

### 6.2 Spatial Exit / Entry Edge Definitions & Geometry

#### Coordinate Frame Conventions
- Frame Dimensions: Width $W$ (default 640), Height $H$ (default 480).
- Bounding Box: $[x_1, y_1, x_2, y_2]$ where $(x_1, y_1)$ is top-left, $(x_2, y_2)$ is bottom-right.
- Bounding Box Center: $c_x = \frac{x_1 + x_2}{2}$, $c_y = \frac{y_1 + y_2}{2}$.
- Threshold Margin: $\delta_x = W \times \text{fraction}$, $\delta_y = H \times \text{fraction}$ (e.g. $\delta_x = 64\text{px}$ for $W=640, \text{fraction}=0.10$).

#### Edge Detection Logic:
1. **Right Edge Exit / Entry**:
   - Proximity Condition: $x_2 \ge W - \delta_x$ or $c_x \ge W - \delta_x$.
   - Direction / Velocity: $\Delta x = x_{\text{recent}} - x_{\text{earlier}} > 0$ (moving East/Right).
2. **Left Edge Exit / Entry**:
   - Proximity Condition: $x_1 \le \delta_x$ or $c_x \le \delta_x$.
   - Direction / Velocity: $\Delta x = x_{\text{recent}} - x_{\text{earlier}} < 0$ for exit, or $\Delta x > 0$ when entering towards frame interior.
3. **Top Edge Exit / Entry**:
   - Proximity Condition: $y_1 \le \delta_y$ or $c_y \le \delta_y$.
   - Direction / Velocity: $\Delta y = y_{\text{recent}} - y_{\text{earlier}} < 0$ (moving North/Up in screen coordinates).
4. **Bottom Edge Exit / Entry**:
   - Proximity Condition: $y_2 \ge H - \delta_y$ or $c_y \ge H - \delta_y$.
   - Direction / Velocity: $\Delta y = y_{\text{recent}} - y_{\text{earlier}} > 0$ (moving South/Down).

---

### 6.3 Incident and Event Schema Extensions

#### Schema: `backend/schemas/events.py`
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class CorrelatedTrackLink(BaseModel):
    incident_id: str
    source_camera_id: str
    source_track_id: str
    source_event_id: Optional[str] = None
    target_camera_id: str
    target_track_id: str
    target_event_id: Optional[str] = None
    object_type: str
    transit_duration_seconds: float
    confidence_band: Literal["HIGH", "MEDIUM", "LOW"]
    edge_match_status: str # e.g. "BOTH_MATCHED", "SOURCE_MATCHED_TARGET_AMBIGUOUS", "AMBIGUOUS"
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    # Cross-camera correlation extension
    incident_id: Optional[str] = None
    correlation_confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    correlated_with_track: Optional[str] = None
    correlated_with_camera: Optional[str] = None
    transit_time_seconds: Optional[float] = None
```

---

### 6.4 Concurrency & Multi-Track Disambiguation Protocol

```
                                  [ New Track Enters CAM-02 ]
                                                │
                                                ▼
                                   Find OPEN windows matching:
                                   - target_camera_id == "CAM02"
                                   - object_type == track.object_type
                                   - t_min <= (t_entry - t_exit) <= (t_max + t_grace)
                                                │
                                ┌───────────────┴───────────────┐
                                │                               │
                         0 Windows Found                 >= 1 Window Found
                                │                               │
                                ▼                               ▼
                         No Correlation                 Count candidate windows
                       (Stand-alone Event)              ┌───────┴───────┐
                                                        │               │
                                                  Exactly 1          >= 2 Windows
                                                        │               │
                                                        ▼               ▼
                                                  Evaluate Band   Calculate |Δt - t_expected|
                                                   (HIGH/MED/LOW) for all candidates
                                                        │               │
                                                        │         Are top 2 within
                                                        │         ambiguity_tie_threshold (0.5s)?
                                                        │         ┌─────┴─────┐
                                                        │         │ YES       │ NO
                                                        │         ▼           ▼
                                                        │      DECLINE     Select best candidate
                                                        │      (Tie Skip)  (Smallest |Δt - t_expected|)
                                                        │         │           │
                                                        └─────────┼───────────┘
                                                                  ▼
                                                      Consume Window & Emit Incident
```

---

### 6.5 Correlation Window Lifecycle State Machine

```
              ┌───────────────┐
              │  TRACK EXITS  │
              │    CAM-01     │
              └───────┬───────┘
                      │
                      ▼
               ┌─────────────┐
               │    OPEN     │◄───────────────────┐
               └──────┬──────┘                    │
                      │                           │
          ┌───────────┴───────────┐               │ Keep open until
          │                       │               │ expiry or match
          ▼                       ▼               │
  [ Valid Entry ]        [ Timer Exceeds ]        │
  [   CAM-02    ]        [ t_max + grace ]        │
          │                       │               │
          ▼                       ▼               │
   ┌─────────────┐         ┌─────────────┐        │
   │  CONSUMED   │         │   EXPIRED   │        │
   │  (LINKED)   │         │  (PRUNED)   │        │
   └─────────────┘         └─────────────┘        │
          │                       │               │
          ▼                       ▼               │
   Unified Incident        Evicted from Memory    │
    Emitted & Saved        by Garbage Collector   │
```

---

## 7. Storage Governance & Audit Trail Integration

1. **Storage Retention Tiers**:
   - Single-Camera Routine: `status == "DISMISSED"` or `risk_level in ["LOW", "NORMAL"]` &rarr; Purged first when disk usage $> 90\%$.
   - Correlated High Incident: `confidence_band in ["HIGH", "MEDIUM"]` and `risk_level in ["MEDIUM", "HIGH", "CRITICAL"]` &rarr; Categorized under **Confirmed Incidents** tier (purged last).
   - Operator Held: `is_held == True` &rarr; Never auto-purged under any circumstance.
2. **Audit Logging Invariants**:
   - Manual Dismissal of Correlated Incident: Calls `events_db.log_audit(event_id, operator, 'REVIEWED', reason, notes)` for both constituent camera events.
   - Storage Auto-Purge: When auto-purge deletes correlated evidence, logs `SYSTEM_AUTO_PURGE` action with freed byte count.

---

## 8. Five-Component Handoff Report

### 8.1 Observation
- **Original Request File**: `C:\Users\HEMANTH\Desktop\SKYNET\.agents\ORIGINAL_REQUEST.md` lines 1-60 establishes strict rules: 2-camera adjacency, external configuration, confidence banding (`HIGH`, `MEDIUM`, `LOW`, `NONE`), prohibition of appearance embeddings and N-camera graph logic, verification tests V1-V8, and acceptance criteria.
- **Event Schema**: `backend/schemas/events.py` lines 1-63 defines `EventSchema` with `track_id`, `camera_id`, `risk_level`, `reasons`, `is_held`, `evidence_path`.
- **Event Engine**: `intelligence/event_engine.py` lines 1-136 handles single-camera tracks, zone intrusions, dwell tracking, and generates `EventSchema` entries.
- **Camera Manager**: `backend/camera_manager.py` lines 86-90 prepends `camera_id` to track IDs (`f"{cid}-{t['track_id']}"`) to guarantee multi-camera ID isolation.
- **Storage Governor**: `backend/storage_manager.py` lines 47-76 runs a background retention loop purging non-held routine evidence at 90% disk capacity down to 70%, logging to SQLite audit trail (`backend/api/events_store.py:45-55`).
- **Dashboard UI**: `dashboard/src/App.jsx` lines 185-223 and lines 446-560 renders active event tables and incident details, polling `GET /api/events`.

### 8.2 Logic Chain
1. **Adjacency Configuration Decoupling**: Because hardcoded camera topologies violate maintainability and Rule R1, adjacency mappings must be read from an external YAML specification (`configs/adjacency.yaml`) and validated via Pydantic (`AdjacencyPairConfig`).
2. **Spatial-Temporal Determinism without Visual Embeddings**: Because appearance embeddings (e.g. BoT-SORT features) are strictly forbidden by Rule R3 and compute-heavy on edge devices, correlation must rely exclusively on deterministic coordinate boundary intersections ($x \ge W - \delta_x$), velocity vectors ($dx/dt$), class equality, and transit intervals ($\Delta t \in [t_{min}, t_{max}]$).
3. **Discrete Categorical Banding**: By mapping evaluation outputs directly to categorical bands (`HIGH`, `MEDIUM`, `LOW`, `NONE`) rather than continuous pseudoprobabilities, the system mathematically eliminates overclaiming identity certainty while providing operators with actionable risk grading.
4. **Deterministic Garbage Collection**: In order to pass V7 and avoid unbounded memory growth under continuous traffic, the correlation engine must prune all correlation windows older than $t_{exit} + t_{max} + t_{grace}$ every tick.
5. **Seamless Storage and Audit Integration**: By attaching `incident_id` and `correlation_confidence` directly to the `EventSchema` and persisting to `SQLiteEventStore`, all existing retention tiers, operator holds, and audit logging work out-of-the-box with zero regressions (V8).

### 8.3 Caveats
1. **Two-Camera Boundary Constraint**: This specification is strictly constrained to 2-camera pair correlations. Future N-camera chain tracking would require a separate multi-hop specification.
2. **Clock Synchronization**: The transit timing calculation assumes synchronized timestamps across camera streams. For simulated or single-process streams, `time.time()` provides sub-millisecond precision. For distributed edge cameras in production, NTP/PTP synchronization is required.
3. **No Appearance Verification**: Because appearance Re-ID is forbidden, two distinct persons of the exact same class entering and exiting within the exact same window with identical paths cannot be disambiguated by clothing or facial embeddings. The engine relies on time closeness or declines to link if ambiguous.

### 8.4 Conclusion
The complete specification for the Cross-Camera Spatial-Temporal Correlation Engine is fully formalized, covering all functional requirements (R1-R3), verification criteria (V1-V8), configuration schemas, spatial bounding box math, confidence banding decision tables, concurrency heuristics, garbage collection lifecycles, and storage governance integrations. The architecture is modular, deterministic, explainable, and compliant with all project constraints.

### 8.5 Verification Method
To independently verify this specification during implementation:
1. **Unit Test Suite**: Create `tests/unit/test_correlation_engine.py` implementing test cases for V1 (positive match $\rightarrow$ HIGH), V2 (class mismatch $\rightarrow$ NONE), V3 (timing boundaries $2.9\text{s}, 3.0\text{s}, 15.0\text{s}, 15.1\text{s}, 22.6\text{s}$), V4 (edge mismatch $\rightarrow$ MEDIUM), V6 (multi-track concurrency and tie-break decline), and V7 (1,000 synthetic exits garbage collection memory test).
2. **Integration Simulator**: Run `python -m simulator` or dedicated scenario script `tests/scenarios/test_cross_camera_correlation.py` to simulate a subject traversing CAM01 right edge into CAM02 left edge 3 times back-to-back, asserting unified Incident creation with visible confidence badge within $\le 2$ seconds.
3. **Regression Suite**: Run `pytest` and `python simulator/scenarios/test_scenarios.py` to confirm 100% pass rate across existing single-camera intelligence, ANPR voting, Face quality, and Storage governance.
