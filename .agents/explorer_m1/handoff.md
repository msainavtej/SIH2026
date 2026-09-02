# Technical Implementation Specification & Handoff Report: Milestone 1

**Milestone:** M1 — Configuration Schema, Spatial Boundary & Correlation Engine Core  
**Agent:** `explorer_m1` (Teamwork Explorer)  
**Date:** 2026-08-30  
**Target Files:**
- `configs/adjacency.yaml` (Feature 1)
- `intelligence/boundary.py` (Feature 2)
- `intelligence/correlation.py` (Features 1, 3, 4, 5)
- `tests/unit/test_correlation_engine.py` (Unit Verification V1, V2, V3, V4, V6, V7)

---

## 1. Observation

Direct observations from codebase inspection and requirements analysis:

1. **Requirements (`ORIGINAL_REQUEST.md:18-60`)**:
   - **R1 (Adjacency & Transit)**: Exactly one adjacency pair between two cameras (`CAM01` &rarr; `CAM02`, right exit &rarr; left entry, 3-15s transit time, 7.5s grace window). Must be externally configurable in YAML, not hardcoded.
   - **R2 (Confidence Banding)**: Output discrete categorical bands (`HIGH`, `MEDIUM`, `LOW`, `NONE`) with zero continuous percentages. Safe default: below LOW threshold, NO correlation is created (unlinked events).
   - **R3 (Strict Prohibitions)**: Zero appearance-based Re-ID embeddings (no BoT-SORT features, no OSNet/CNN embeddings) and zero N-camera graph structures. Zero claims of "confirmed identity" or "same person".
   - **V1 (Positive Match)**: CAM01 right exit + CAM02 left entry within 3-15s &rarr; Incident created with `confidence == "HIGH"`.
   - **V2 (Class Mismatch)**: `person` exits CAM01, `car` enters CAM02 &rarr; NOT linked.
   - **V3 (Timing Boundaries)**: $\Delta t = 2.9\text{s}$ &rarr; `NONE`; $3.0\text{s}$ &rarr; `HIGH`; $15.0\text{s}$ &rarr; `HIGH`; $15.1\text{s}$ &rarr; `LOW`; $22.6\text{s}$ &rarr; `NONE`.
   - **V4 (Edge Mismatch)**: Exit top instead of right &rarr; downgrades to `MEDIUM`, never upgrades to `HIGH`.
   - **V6 (Concurrency)**: Multi-track disambiguation selects closest timing ($|\Delta t - t_{expected}|$) or declines link if ambiguous within tie threshold ($0.5\text{s}$). 1-to-1 matching invariant enforced.
   - **V7 (Cleanup)**: Open windows expire after $t_{exit} + t_{max} + t_{grace}$ ($22.5\text{s}$) and are purged by garbage collection to guarantee $O(k)$ memory bounding.

2. **Existing Codebase Architecture**:
   - `backend/schemas/events.py:5-38`: Defines `TrackedObject` (`bbox: List[int]`, `object_type: str`, `track_id: str`, `confidence: float`) and `EventSchema`.
   - `ai/tracking/trajectory.py:4-56`: Tracks historical coordinates as deques of `[center_x, center_y]` with `max_history=30`.
   - `intelligence/direction.py:1-45`: Computes compass directions (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`) from trajectory point pairs using screen coordinate math (inverted Y axis).
   - `backend/camera_manager.py:85-90`: Prepends camera IDs to track identifiers (e.g. `CAM01-P1`, `CAM02-P2`) to ensure multi-camera isolation.
   - `intelligence/risk.py:1-120`: Loads configuration from `configs/rules.yaml` and `configs/anpr.yaml` via `yaml.safe_load`.
   - `backend/api/events_store.py:10-128`: SQLite persistence layer (`storage/events.db`) supporting event caching and audit logs.

3. **Current Missing Components**:
   - `configs/adjacency.yaml` does not exist yet.
   - `intelligence/boundary.py` does not exist yet.
   - `intelligence/correlation.py` does not exist yet.
   - `tests/unit/test_correlation_engine.py` does not exist yet.

---

## 2. Logic Chain

1. **Decoupling via YAML Configuration**:
   - Hardcoding camera topology violates Rule R1 and prevents adapting to new camera placements.
   - Therefore, `configs/adjacency.yaml` must define the topology (`source_camera_id`, `target_camera_id`), spatial edges (`source_exit_edge`, `target_entry_edge`, `edge_threshold_fraction`), timing bounds (`min_transit_seconds`, `max_transit_seconds`, `grace_window_seconds`, `ambiguity_tie_threshold_s`), and confidence thresholds (`detection_conf_threshold`).
   - Pydantic v2 models (`AdjacencyPairConfig`) validate all ranges at initialization time ($t_{min} \le t_{max}$, fractions $\in [0.01, 0.50]$).

2. **Pure Geometric Spatial Edge Boundary Analysis (No Embeddings)**:
   - To satisfy Rule R3 and keep edge compute lightweight, `SpatialBoundaryAnalyzer` evaluates bounding box edge proximity and trajectory displacement vectors.
   - Screen coordinate frame ($W=640, H=480$):
     - `right`: $x_2 \ge W - \delta_x$ or $c_x \ge W - \delta_x$, trajectory $\Delta x > 0$.
     - `left`: $x_1 \le \delta_x$ or $c_x \le \delta_x$, trajectory $\Delta x < 0$ (for exit) or $\Delta x > 0$ (for entry).
     - `top`: $y_1 \le \delta_y$ or $c_y \le \delta_y$, trajectory $\Delta y < 0$.
     - `bottom`: $y_2 \ge H - \delta_y$ or $c_y \ge H - \delta_y$, trajectory $\Delta y > 0$.
   - Where margin $\delta_x = W \times \text{fraction}$, $\delta_y = H \times \text{fraction}$ (default $0.10 \times 640 = 64\text{px}$).

3. **Correlation Window State Machine & Deterministic GC**:
   - An exit event on `source_camera_id` transitions state to `OPEN`.
   - A valid matching entry on `target_camera_id` consumes the window &rarr; `CONSUMED` &rarr; Incident emitted.
   - A window with no match past $t_{exit} + t_{max} + t_{grace}$ (22.5s) transitions to `EXPIRED` and is pruned by `cleanup_expired()` on each cycle.
   - Enforcing a maximum active window cap (`max_active_windows = 200`) provides a circuit breaker against memory spikes (Rule V7).

4. **Categorical Confidence Band Evaluation (R2, V1-V4)**:
   - If `object_type` does not match: Band = `NONE` (Rule V2).
   - If $\Delta t < t_{min}$ or $\Delta t > t_{max} + t_{grace}$: Band = `NONE` (Rule V3).
   - If $t_{min} \le \Delta t \le t_{max}$:
     - If both edges match and $\min(conf_{src}, conf_{tgt}) \ge 0.50$: Band = `HIGH` (Rule V1).
     - If one/both edges are ambiguous/mismatched and $conf \ge 0.50$: Band = `MEDIUM` (Rule V4).
     - If both edges match but detection confidence $< 0.50$: Band = `LOW`.
   - If $t_{max} < \Delta t \le t_{max} + t_{grace}$: Band = `LOW` (Rule V3).
   - Safe default: Any evaluation below `LOW` emits `NONE`; no Incident is created.

5. **1-to-1 Concurrency Disambiguation Protocol (Rule V6)**:
   - When multiple candidate windows are open for an entering track:
     - Compute distance $d_i = |\Delta t_i - t_{expected}|$ for each candidate window $W_i$.
     - If $|d_{(2)} - d_{(1)}| < \text{ambiguity\_tie\_threshold\_s}$ (0.5s): Near-equidistant tie &rarr; **Decline to link** (`NONE`). Prevents arbitrary guessing.
     - Else: Select $W_{(1)}$ with minimum distance, mark $W_{(1)}$ as `CONSUMED`, leave other windows `OPEN`.
   - When a single exit has multiple entries arriving sequentially: First arrival consumes window; subsequent arrivals find 0 open windows &rarr; stand-alone unlinked events.

---

## 3. Caveats

1. **Two-Camera Scope**: The configuration and correlation engine are strictly designed for single pairs (2 cameras). Multi-hop camera graph solvers are explicitly out of scope per Rule R3.
2. **Timestamp Source**: The engine relies on numeric Unix epoch timestamps (`time.time()` float seconds). Live production environments require sub-second NTP synchronization between edge nodes.
3. **Trajectory History Depth**: If a track is detected for only 1 frame upon entry at the edge, trajectory displacement is unavailable; proximity alone satisfies the entry edge check.

---

## 4. Conclusion & Complete Technical Implementation Blueprint

The following technical blueprints provide the exact implementation specifications for the Worker agent.

### 4.1 Feature 1: `configs/adjacency.yaml`

```yaml
# ==============================================================================
# SKYNET CROSS-CAMERA ADJACENCY & SPATIAL-TEMPORAL TOPOLOGY CONFIGURATION
# ==============================================================================
# Defines directional spatial linkage from Source Camera to Target Camera
# without appearance-based Re-ID embeddings.
# ==============================================================================

adjacency_map:
  pair_id: "ADJ_CAM01_CAM02"
  enabled: true
  source_camera_id: "CAM01"
  target_camera_id: "CAM02"

  # Spatial boundary edge definitions
  spatial_edges:
    source_exit_edge: "right"        # Allowed: "left", "right", "top", "bottom"
    target_entry_edge: "left"        # Allowed: "left", "right", "top", "bottom"
    edge_threshold_fraction: 0.10    # 10% of frame dimension (e.g., 64px on 640w)
    min_trajectory_points: 3         # Minimum trajectory points for velocity vector check

  # Temporal transit parameters (seconds)
  transit_timing:
    min_transit_seconds: 3.0         # Minimum plausible physical transit time
    max_transit_seconds: 15.0        # Upper bound of core transit window
    grace_window_seconds: 7.5        # Grace window (+50% of max_transit -> 22.5s total)
    ambiguity_tie_threshold_s: 0.5   # Tie-break threshold: decline link if candidates tie within 0.5s
    expected_transit_seconds: 9.0    # Expected transit time: (3.0 + 15.0) / 2.0 = 9.0s

  # Categorical confidence evaluation rules
  confidence_rules:
    detection_conf_threshold: 0.50   # Minimum YOLO detection confidence for HIGH score
    allow_ambiguous_edge_medium: true # Allow downgrade to MEDIUM if edge is ambiguous
    allow_grace_window_low: true     # Allow LOW confidence in grace window

  # Memory & Garbage Collection parameters
  lifecycle:
    gc_interval_seconds: 1.0         # Frequency of background GC checks (seconds)
    max_active_windows: 200          # Circuit breaker capacity limit for open windows
```

---

### 4.2 Feature 2: `intelligence/boundary.py`

```python
"""
intelligence/boundary.py

Spatial Edge Boundary Detection and Trajectory Velocity Analyzer.
Evaluates bounding box spatial proximity to image edges and computes directional
velocity vectors without using appearance embeddings.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any, Literal
import math


@dataclass
class EdgeEvaluationResult:
    """Result of evaluating a track's spatial edge proximity and trajectory vector."""
    proximity_matched: bool
    vector_matched: bool
    configured_edge: str
    detected_edge: Optional[str]
    is_valid: bool
    details: Dict[str, Any] = field(default_factory=dict)


class SpatialBoundaryAnalyzer:
    """
    Analyzes whether a bounding box and historical trajectory intersect
    a configured frame edge (LEFT, RIGHT, TOP, BOTTOM) and exhibit the correct
    directional velocity vector.
    """

    VALID_EDGES = {"left", "right", "top", "bottom"}

    def __init__(
        self,
        edge_threshold_fraction: float = 0.10,
        min_trajectory_points: int = 3,
        default_frame_size: Tuple[int, int] = (640, 480)
    ):
        """
        Initialize the spatial boundary analyzer.

        :param edge_threshold_fraction: Fraction of frame dimension defining boundary margin (0.01 - 0.50).
        :param min_trajectory_points: Minimum trajectory points required for velocity vector check.
        :param default_frame_size: Default (width, height) in pixels.
        """
        self.edge_threshold_fraction = edge_threshold_fraction
        self.min_trajectory_points = min_trajectory_points
        self.default_frame_size = default_frame_size

    def check_edge_proximity(
        self,
        bbox: List[int],
        edge: str,
        frame_size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Check if bounding box [x1, y1, x2, y2] is within the threshold margin of the specified edge.

        :param bbox: [x1, y1, x2, y2]
        :param edge: "left", "right", "top", "bottom"
        :param frame_size: (width, height) tuple
        :return: True if bbox intersects edge boundary region
        """
        if not bbox or len(bbox) < 4:
            return False

        w, h = frame_size or self.default_frame_size
        edge = edge.lower()
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        dx_thresh = w * self.edge_threshold_fraction
        dy_thresh = h * self.edge_threshold_fraction

        if edge == "right":
            return x2 >= (w - dx_thresh) or cx >= (w - dx_thresh)
        elif edge == "left":
            return x1 <= dx_thresh or cx <= dx_thresh
        elif edge == "top":
            return y1 <= dy_thresh or cy <= dy_thresh
        elif edge == "bottom":
            return y2 >= (h - dy_thresh) or cy >= (h - dy_thresh)
        return False

    def detect_closest_edge(
        self,
        bbox: List[int],
        frame_size: Optional[Tuple[int, int]] = None
    ) -> Optional[str]:
        """
        Detects which frame edge (if any) the bounding box is currently closest to / touching.

        :param bbox: [x1, y1, x2, y2]
        :param frame_size: (width, height) tuple
        :return: "left", "right", "top", "bottom", or None
        """
        for edge in ["right", "left", "top", "bottom"]:
            if self.check_edge_proximity(bbox, edge, frame_size):
                return edge
        return None

    def check_trajectory_vector(
        self,
        trajectory: List[List[int]],
        edge: str,
        mode: Literal["exit", "entry"] = "exit"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Computes directional displacement vector from trajectory history.

        :param trajectory: List of [x, y] coordinates in chronological order.
        :param edge: "left", "right", "top", "bottom"
        :param mode: "exit" (moving towards/out of edge) or "entry" (moving away/in from edge).
        :return: (vector_matched, metadata_dict)
        """
        edge = edge.lower()
        if not trajectory or len(trajectory) < self.min_trajectory_points:
            # Insufficient points: for entry, newly appearing object may only have 1-2 points
            if mode == "entry":
                return True, {"reason": "insufficient_points_entry_permissive", "point_count": len(trajectory) if trajectory else 0}
            return False, {"reason": "insufficient_points_exit", "point_count": len(trajectory) if trajectory else 0}

        # Calculate displacement from oldest relevant point to newest point
        p_start = trajectory[0]
        p_end = trajectory[-1]
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]  # Note: screen coords Y increases downwards

        matched = False
        if mode == "exit":
            if edge == "right":
                matched = dx > 0 and abs(dx) >= abs(dy) * 0.5  # Moving eastward
            elif edge == "left":
                matched = dx < 0 and abs(dx) >= abs(dy) * 0.5  # Moving westward
            elif edge == "top":
                matched = dy < 0 and abs(dy) >= abs(dx) * 0.5  # Moving northward (up)
            elif edge == "bottom":
                matched = dy > 0 and abs(dy) >= abs(dx) * 0.5  # Moving southward (down)
        else:  # mode == "entry"
            if edge == "right":
                matched = dx < 0  # Entered right edge, moving inward (westward)
            elif edge == "left":
                matched = dx > 0  # Entered left edge, moving inward (eastward)
            elif edge == "top":
                matched = dy > 0  # Entered top edge, moving inward (southward)
            elif edge == "bottom":
                matched = dy < 0  # Entered bottom edge, moving inward (northward)

        meta = {
            "dx": dx,
            "dy": dy,
            "mode": mode,
            "edge": edge,
            "point_count": len(trajectory),
            "matched": matched
        }
        return matched, meta

    def evaluate_edge_crossing(
        self,
        bbox: List[int],
        trajectory: List[List[int]],
        configured_edge: str,
        frame_size: Optional[Tuple[int, int]] = None,
        mode: Literal["exit", "entry"] = "exit"
    ) -> EdgeEvaluationResult:
        """
        Comprehensive spatial evaluation combining proximity and trajectory vector.

        :param bbox: [x1, y1, x2, y2]
        :param trajectory: List of [x, y] coordinates
        :param configured_edge: Configured expected edge
        :param frame_size: (width, height)
        :param mode: "exit" or "entry"
        :return: EdgeEvaluationResult
        """
        configured_edge = configured_edge.lower()
        prox_matched = self.check_edge_proximity(bbox, configured_edge, frame_size)
        detected_edge = self.detect_closest_edge(bbox, frame_size)
        vec_matched, vec_meta = self.check_trajectory_vector(trajectory, configured_edge, mode=mode)

        is_valid = prox_matched and (vec_matched or (mode == "entry" and len(trajectory) < self.min_trajectory_points))

        return EdgeEvaluationResult(
            proximity_matched=prox_matched,
            vector_matched=vec_matched,
            configured_edge=configured_edge,
            detected_edge=detected_edge,
            is_valid=is_valid,
            details={
                "proximity_matched": prox_matched,
                "vector_matched": vec_matched,
                "vector_meta": vec_meta,
                "detected_edge": detected_edge,
                "configured_edge": configured_edge,
                "mode": mode
            }
        )
```

---

### 4.3 Feature 3, 4, 5: `intelligence/correlation.py`

```python
"""
intelligence/correlation.py

Cross-Camera Spatial-Temporal Correlation Engine.
Links track segments across adjacent cameras using external YAML configuration,
bounding box spatial vectors, and temporal transit windows without appearance embeddings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Literal
import os
import time
import uuid
import yaml
from pydantic import BaseModel, Field, model_validator

from intelligence.boundary import SpatialBoundaryAnalyzer, EdgeEvaluationResult


# ------------------------------------------------------------------------------
# Pydantic Configuration Models (Feature 1)
# ------------------------------------------------------------------------------

class SpatialEdgesConfig(BaseModel):
    source_exit_edge: Literal["left", "right", "top", "bottom"] = "right"
    target_entry_edge: Literal["left", "right", "top", "bottom"] = "left"
    edge_threshold_fraction: float = Field(default=0.10, ge=0.01, le=0.50)
    min_trajectory_points: int = Field(default=3, ge=1)


class TransitTimingConfig(BaseModel):
    min_transit_seconds: float = Field(default=3.0, ge=0.0)
    max_transit_seconds: float = Field(default=15.0, ge=0.1)
    grace_window_seconds: float = Field(default=7.5, ge=0.0)
    ambiguity_tie_threshold_s: float = Field(default=0.5, ge=0.0)
    expected_transit_seconds: Optional[float] = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.min_transit_seconds > self.max_transit_seconds:
            raise ValueError(
                f"min_transit_seconds ({self.min_transit_seconds}) cannot exceed max_transit_seconds ({self.max_transit_seconds})"
            )
        return self

    def get_expected_transit(self) -> float:
        if self.expected_transit_seconds is not None:
            return self.expected_transit_seconds
        return (self.min_transit_seconds + self.max_transit_seconds) / 2.0


class ConfidenceRulesConfig(BaseModel):
    detection_conf_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    allow_ambiguous_edge_medium: bool = True
    allow_grace_window_low: bool = True


class LifecycleConfig(BaseModel):
    gc_interval_seconds: float = Field(default=1.0, ge=0.1)
    max_active_windows: int = Field(default=200, ge=1)


class AdjacencyPairConfig(BaseModel):
    pair_id: str
    enabled: bool = True
    source_camera_id: str
    target_camera_id: str
    spatial_edges: SpatialEdgesConfig = Field(default_factory=SpatialEdgesConfig)
    transit_timing: TransitTimingConfig = Field(default_factory=TransitTimingConfig)
    confidence_rules: ConfidenceRulesConfig = Field(default_factory=ConfidenceRulesConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)


class AdjacencyRootConfig(BaseModel):
    adjacency_map: AdjacencyPairConfig


# ------------------------------------------------------------------------------
# Data Models & Enums (Features 3, 4)
# ------------------------------------------------------------------------------

class WindowStatus(str, Enum):
    OPEN = "OPEN"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass
class CorrelationWindow:
    """Represents an active spatial-temporal correlation window opened on track exit."""
    window_id: str
    source_camera_id: str
    source_track_id: str
    object_type: str
    exit_timestamp: float
    exit_bbox: List[int]
    exit_edge_matched: bool
    exit_edge_name: Optional[str]
    detection_confidence: float
    status: WindowStatus = WindowStatus.OPEN
    matched_entry_track_id: Optional[str] = None
    matched_incident_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class CorrelatedTrackLink:
    """Represents a unified cross-camera correlation incident linking two tracks."""
    incident_id: str
    pair_id: str
    source_camera_id: str
    source_track_id: str
    target_camera_id: str
    target_track_id: str
    object_type: str
    transit_duration_seconds: float
    confidence_band: str  # "HIGH", "MEDIUM", "LOW"
    edge_match_status: str  # "BOTH_MATCHED", "SOURCE_MATCHED_TARGET_AMBIGUOUS", "AMBIGUOUS"
    detection_confidence: float
    source_exit_time: float
    target_entry_time: float
    created_at: float = field(default_factory=time.time)


# ------------------------------------------------------------------------------
# Core Spatial-Temporal Correlation Engine (Features 3, 4, 5)
# ------------------------------------------------------------------------------

class SpatialTemporalCorrelationEngine:
    """
    Deterministic Cross-Camera Correlation Engine.
    Executes spatial edge verification, transit window evaluation, categorical
    confidence banding, and concurrency disambiguation for a configured camera pair.
    """

    def __init__(
        self,
        config_path: Optional[str] = "configs/adjacency.yaml",
        config: Optional[AdjacencyPairConfig] = None
    ):
        if config is not None:
            self.config = config
        elif config_path and os.path.exists(config_path):
            self.config = self.load_config(config_path)
        else:
            # Fallback default configuration
            self.config = AdjacencyPairConfig(
                pair_id="ADJ_CAM01_CAM02",
                source_camera_id="CAM01",
                target_camera_id="CAM02"
            )

        self.boundary_analyzer = SpatialBoundaryAnalyzer(
            edge_threshold_fraction=self.config.spatial_edges.edge_threshold_fraction,
            min_trajectory_points=self.config.spatial_edges.min_trajectory_points
        )

        self.active_windows: Dict[str, CorrelationWindow] = {}
        self.last_gc_time: float = 0.0

        # Operational metrics
        self.metrics = {
            "total_windows_opened": 0,
            "total_correlated": 0,
            "total_expired": 0,
            "total_declined_ties": 0,
            "total_class_mismatches": 0,
            "total_timing_rejections": 0
        }

    @staticmethod
    def load_config(config_path: str) -> AdjacencyPairConfig:
        """Load and validate external YAML configuration."""
        with open(config_path, "r") as f:
            raw_yaml = yaml.safe_load(f)
        root = AdjacencyRootConfig.model_validate(raw_yaml)
        return root.adjacency_map

    def on_track_exit(
        self,
        camera_id: str,
        track: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> Optional[CorrelationWindow]:
        """
        Hook called when a track exits or terminates on a camera.
        Opens a correlation window if camera is the configured source camera.

        :param camera_id: Identifier of camera emitting track exit.
        :param track: Track dictionary containing track_id, object_type, bbox, trajectory, confidence.
        :param timestamp: Exit epoch timestamp in seconds.
        :return: CorrelationWindow instance if opened, else None.
        """
        if not self.config.enabled:
            return None

        if camera_id != self.config.source_camera_id:
            return None

        t_now = timestamp if timestamp is not None else time.time()

        # Perform periodic GC cleanup
        if t_now - self.last_gc_time >= self.config.lifecycle.gc_interval_seconds:
            self.cleanup_expired(t_now)

        # Circuit breaker memory cap
        if len(self.active_windows) >= self.config.lifecycle.max_active_windows:
            self.cleanup_expired(t_now)
            if len(self.active_windows) >= self.config.lifecycle.max_active_windows:
                # Evict oldest window to protect memory
                oldest_key = min(self.active_windows.keys(), key=lambda k: self.active_windows[k].exit_timestamp)
                del self.active_windows[oldest_key]
                self.metrics["total_expired"] += 1

        bbox = track.get("bbox", [0, 0, 0, 0])
        trajectory = track.get("trajectory", [])
        edge_eval = self.boundary_analyzer.evaluate_edge_crossing(
            bbox=bbox,
            trajectory=trajectory,
            configured_edge=self.config.spatial_edges.source_exit_edge,
            mode="exit"
        )

        window_id = f"WIN-{uuid.uuid4().hex[:8]}"
        window = CorrelationWindow(
            window_id=window_id,
            source_camera_id=camera_id,
            source_track_id=str(track.get("track_id", "")),
            object_type=str(track.get("object_type", "unknown")),
            exit_timestamp=t_now,
            exit_bbox=list(bbox),
            exit_edge_matched=edge_eval.proximity_matched,
            exit_edge_name=edge_eval.detected_edge,
            detection_confidence=float(track.get("confidence", 1.0)),
            status=WindowStatus.OPEN
        )

        self.active_windows[window_id] = window
        self.metrics["total_windows_opened"] += 1
        return window

    def on_track_entry(
        self,
        camera_id: str,
        track: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> Optional[CorrelatedTrackLink]:
        """
        Hook called when a new track is initialized or enters on a camera.
        Finds candidate OPEN windows, disambiguates ties, and performs correlation.

        :param camera_id: Identifier of camera emitting track entry.
        :param track: Track dictionary containing track_id, object_type, bbox, trajectory, confidence.
        :param timestamp: Entry epoch timestamp in seconds.
        :return: CorrelatedTrackLink if matched, else None.
        """
        if not self.config.enabled:
            return None

        if camera_id != self.config.target_camera_id:
            return None

        t_now = timestamp if timestamp is not None else time.time()
        self.cleanup_expired(t_now)

        track_type = track.get("object_type", "unknown")
        min_t = self.config.transit_timing.min_transit_seconds
        max_t = self.config.transit_timing.max_transit_seconds
        grace_t = self.config.transit_timing.grace_window_seconds
        total_window_t = max_t + grace_t
        t_expected = self.config.transit_timing.get_expected_transit()
        tie_threshold = self.config.transit_timing.ambiguity_tie_threshold_s

        # 1. Filter candidate OPEN windows matching class and broad temporal boundary
        candidate_windows: List[Tuple[CorrelationWindow, float, float]] = []
        for win in self.active_windows.values():
            if win.status != WindowStatus.OPEN:
                continue

            # Class compatibility check (Rule R2, V2)
            if win.object_type != track_type:
                self.metrics["total_class_mismatches"] += 1
                continue

            dt = t_now - win.exit_timestamp

            # Timing check: must be >= min_t and <= total_window_t (Rule V3)
            if dt < min_t or dt > total_window_t:
                self.metrics["total_timing_rejections"] += 1
                continue

            # Distance from expected transit time for time-closeness heuristic
            dist_expected = abs(dt - t_expected)
            candidate_windows.append((win, dt, dist_expected))

        if not candidate_windows:
            return None

        # 2. Concurrency & Disambiguation Protocol (Rule V6)
        if len(candidate_windows) == 1:
            best_window, dt, _ = candidate_windows[0]
        else:
            # Multiple candidate windows: sort by closeness to expected transit time
            candidate_windows.sort(key=lambda item: item[2])
            top_candidate, dt_top, dist_top = candidate_windows[0]
            second_candidate, dt_second, dist_second = candidate_windows[1]

            # Check for ambiguity tie within threshold
            if abs(dist_second - dist_top) < tie_threshold:
                # Ambiguous tie: decline to link rather than guessing (Rule V6, E12)
                self.metrics["total_declined_ties"] += 1
                return None

            best_window = top_candidate

        # 3. Evaluate Confidence Band
        link = self.evaluate_correlation(best_window, track, t_now)
        if link is not None:
            best_window.status = WindowStatus.CONSUMED
            best_window.matched_entry_track_id = str(track.get("track_id", ""))
            best_window.matched_incident_id = link.incident_id
            self.metrics["total_correlated"] += 1
            return link

        return None

    def evaluate_correlation(
        self,
        window: CorrelationWindow,
        entry_track: Dict[str, Any],
        entry_timestamp: float
    ) -> Optional[CorrelatedTrackLink]:
        """
        Evaluates categorical confidence score (HIGH, MEDIUM, LOW, NONE)
        based on class match, spatial edge verification, transit timing, and detection quality.

        :param window: Source CorrelationWindow
        :param entry_track: Candidate target track dict
        :param entry_timestamp: Entry epoch timestamp
        :return: CorrelatedTrackLink if confidence >= LOW, else None.
        """
        # 1. Class match check
        class_match = (window.object_type == entry_track.get("object_type"))
        if not class_match:
            return None

        # 2. Timing band calculation
        dt = entry_timestamp - window.exit_timestamp
        min_t = self.config.transit_timing.min_transit_seconds
        max_t = self.config.transit_timing.max_transit_seconds
        grace_t = self.config.transit_timing.grace_window_seconds

        if dt < min_t:
            return None  # TOO_FAST -> NONE
        elif min_t <= dt <= max_t:
            timing_band = "CORE"
        elif max_t < dt <= (max_t + grace_t):
            timing_band = "GRACE"
        else:
            return None  # EXPIRED -> NONE

        # 3. Spatial Edge Verification
        entry_bbox = entry_track.get("bbox", [0, 0, 0, 0])
        entry_traj = entry_track.get("trajectory", [])
        entry_eval = self.boundary_analyzer.evaluate_edge_crossing(
            bbox=entry_bbox,
            trajectory=entry_traj,
            configured_edge=self.config.spatial_edges.target_entry_edge,
            mode="entry"
        )

        source_edge_ok = window.exit_edge_matched
        target_edge_ok = entry_eval.proximity_matched
        both_edges_matched = source_edge_ok and target_edge_ok

        if both_edges_matched:
            edge_status = "BOTH_MATCHED"
        elif source_edge_ok and not target_edge_ok:
            edge_status = "SOURCE_MATCHED_TARGET_AMBIGUOUS"
        elif not source_edge_ok and target_edge_ok:
            edge_status = "SOURCE_AMBIGUOUS_TARGET_MATCHED"
        else:
            edge_status = "AMBIGUOUS"

        # 4. Detection quality check
        theta_det = self.config.confidence_rules.detection_conf_threshold
        src_conf = window.detection_confidence
        tgt_conf = float(entry_track.get("confidence", 1.0))
        detection_quality_ok = (src_conf >= theta_det and tgt_conf >= theta_det)

        # 5. Decision Matrix (Rule R2, V1-V4)
        band = ConfidenceBand.NONE

        if timing_band == "CORE":
            if both_edges_matched and detection_quality_ok:
                band = ConfidenceBand.HIGH  # Rule V1
            elif not both_edges_matched and detection_quality_ok:
                if self.config.confidence_rules.allow_ambiguous_edge_medium:
                    band = ConfidenceBand.MEDIUM  # Rule V4
                else:
                    band = ConfidenceBand.NONE
            elif both_edges_matched and not detection_quality_ok:
                band = ConfidenceBand.LOW  # Low detection conf downgrade
            else:
                band = ConfidenceBand.NONE
        elif timing_band == "GRACE":
            if self.config.confidence_rules.allow_grace_window_low and detection_quality_ok:
                band = ConfidenceBand.LOW  # Rule V3 grace window
            else:
                band = ConfidenceBand.NONE

        if band == ConfidenceBand.NONE:
            return None

        # Format incident identifier
        date_str = time.strftime("%Y%m%d", time.gmtime(entry_timestamp))
        incident_id = f"INC-{date_str}-{uuid.uuid4().hex[:6]}"

        return CorrelatedTrackLink(
            incident_id=incident_id,
            pair_id=self.config.pair_id,
            source_camera_id=window.source_camera_id,
            source_track_id=window.source_track_id,
            target_camera_id=self.config.target_camera_id,
            target_track_id=str(entry_track.get("track_id", "")),
            object_type=window.object_type,
            transit_duration_seconds=round(dt, 2),
            confidence_band=band.value,
            edge_match_status=edge_status,
            detection_confidence=min(src_conf, tgt_conf),
            source_exit_time=window.exit_timestamp,
            target_entry_time=entry_timestamp
        )

    def cleanup_expired(self, current_timestamp: float) -> int:
        """
        Purges expired correlation windows beyond t_exit + max_transit + grace_window.
        Guarantees O(k) bounded memory with zero unbounded growth (Rule V7).

        :param current_timestamp: Current epoch timestamp in seconds.
        :return: Count of purged windows.
        """
        self.last_gc_time = current_timestamp
        max_t = self.config.transit_timing.max_transit_seconds
        grace_t = self.config.transit_timing.grace_window_seconds
        cutoff_duration = max_t + grace_t

        keys_to_purge = []
        for win_id, win in self.active_windows.items():
            age = current_timestamp - win.exit_timestamp
            if win.status == WindowStatus.CONSUMED:
                # Consumed windows can be immediately cleaned or kept briefly
                if age > cutoff_duration:
                    keys_to_purge.append(win_id)
            elif age > cutoff_duration:
                win.status = WindowStatus.EXPIRED
                keys_to_purge.append(win_id)

        for win_id in keys_to_purge:
            del self.active_windows[win_id]
            self.metrics["total_expired"] += 1

        return len(keys_to_purge)
```

---

### 4.4 Feature Verification Test Suite: `tests/unit/test_correlation_engine.py`

```python
"""
tests/unit/test_correlation_engine.py

Comprehensive Unit Test Suite for Milestone 1:
- V1: Positive Match -> HIGH confidence Incident linking both track IDs
- V2: Class Mismatch -> NONE (not linked)
- V3: Timing Boundaries -> 2.9s (NONE), 3.0s (HIGH), 15.0s (HIGH), 15.1s (LOW), 22.6s (NONE)
- V4: Edge Mismatch / Downgrades -> Top exit -> MEDIUM (never upgrades to HIGH)
- V6: Concurrency & Disambiguation -> Time-closeness selection, tie-break declination, 1-to-1 invariant
- V7: Lifecycle & Memory Bounding -> 1,000 synthetic exits garbage collection without leaks
"""

import pytest
import time
from intelligence.boundary import SpatialBoundaryAnalyzer
from intelligence.correlation import (
    SpatialTemporalCorrelationEngine,
    AdjacencyPairConfig,
    SpatialEdgesConfig,
    TransitTimingConfig,
    ConfidenceRulesConfig,
    LifecycleConfig,
    ConfidenceBand,
    WindowStatus
)


@pytest.fixture
def test_config():
    """Default test configuration fixture with standard parameters."""
    return AdjacencyPairConfig(
        pair_id="ADJ_CAM01_CAM02",
        enabled=True,
        source_camera_id="CAM01",
        target_camera_id="CAM02",
        spatial_edges=SpatialEdgesConfig(
            source_exit_edge="right",
            target_entry_edge="left",
            edge_threshold_fraction=0.10,
            min_trajectory_points=3
        ),
        transit_timing=TransitTimingConfig(
            min_transit_seconds=3.0,
            max_transit_seconds=15.0,
            grace_window_seconds=7.5,
            ambiguity_tie_threshold_s=0.5,
            expected_transit_seconds=9.0
        ),
        confidence_rules=ConfidenceRulesConfig(
            detection_conf_threshold=0.50,
            allow_ambiguous_edge_medium=True,
            allow_grace_window_low=True
        ),
        lifecycle=LifecycleConfig(
            gc_interval_seconds=1.0,
            max_active_windows=200
        )
    )


@pytest.fixture
def engine(test_config):
    """Engine instance initialized with test configuration."""
    return SpatialTemporalCorrelationEngine(config=test_config)


# ==============================================================================
# V1: Positive Match Unit Test
# ==============================================================================

def test_v1_positive_match(engine):
    """
    V1: CAM-01 track exits right edge at t=100.0s; same-class track enters CAM-02 left edge at t=105.0s.
    Asserts unified Incident is created linking track IDs with HIGH confidence.
    """
    t_exit = 100.0
    exit_track = {
        "track_id": "CAM01-P1",
        "object_type": "person",
        "confidence": 0.92,
        "bbox": [585, 200, 635, 300],  # Right edge of 640x480
        "trajectory": [[500, 250], [550, 250], [610, 250]]  # Moving East
    }
    window = engine.on_track_exit("CAM01", exit_track, timestamp=t_exit)
    assert window is not None
    assert window.status == WindowStatus.OPEN
    assert window.exit_edge_matched is True

    t_entry = 105.0  # Delta t = 5.0s (in [3.0, 15.0])
    entry_track = {
        "track_id": "CAM02-P2",
        "object_type": "person",
        "confidence": 0.88,
        "bbox": [10, 200, 60, 300],  # Left edge of 640x480
        "trajectory": [[15, 250], [35, 250]]  # Moving East into frame
    }
    link = engine.on_track_entry("CAM02", entry_track, timestamp=t_entry)
    assert link is not None
    assert link.confidence_band == "HIGH"
    assert link.source_track_id == "CAM01-P1"
    assert link.target_track_id == "CAM02-P2"
    assert link.object_type == "person"
    assert link.transit_duration_seconds == 5.0
    assert link.edge_match_status == "BOTH_MATCHED"
    assert window.status == WindowStatus.CONSUMED


# ==============================================================================
# V2: Object Class Mismatch Unit Test
# ==============================================================================

def test_v2_class_mismatch(engine):
    """
    V2: Person exits CAM-01 at t=100.0s; car enters CAM-02 at t=105.0s.
    Asserts tracks remain unlinked; no Incident is created.
    """
    t_exit = 100.0
    exit_track = {
        "track_id": "CAM01-P1",
        "object_type": "person",
        "confidence": 0.90,
        "bbox": [590, 200, 638, 300],
        "trajectory": [[520, 250], [570, 250], [610, 250]]
    }
    window = engine.on_track_exit("CAM01", exit_track, timestamp=t_exit)
    assert window is not None

    t_entry = 105.0
    entry_track = {
        "track_id": "CAM02-C1",
        "object_type": "car",  # Mismatch!
        "confidence": 0.95,
        "bbox": [5, 200, 70, 300],
        "trajectory": [[10, 250], [30, 250]]
    }
    link = engine.on_track_entry("CAM02", entry_track, timestamp=t_entry)
    assert link is None
    assert window.status == WindowStatus.OPEN  # Window remains open for person


# ==============================================================================
# V3: Transit Timing Boundaries Unit Test
# ==============================================================================

def test_v3_timing_boundaries(engine):
    """
    V3: Tests timing boundaries:
    - 2.9s (dt < 3.0s min) -> NONE
    - 3.0s (dt == min_transit inclusive) -> HIGH
    - 15.0s (dt == max_transit inclusive) -> HIGH
    - 15.1s (dt in grace window (15.0, 22.5]) -> LOW
    - 22.6s (dt > 22.5s expired) -> NONE
    """
    # 1. dt = 2.9s (Too fast)
    engine_fast = SpatialTemporalCorrelationEngine(config=engine.config)
    engine_fast.on_track_exit("CAM01", {"track_id": "CAM01-P1", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}, timestamp=100.0)
    link_fast = engine_fast.on_track_entry("CAM02", {"track_id": "CAM02-P2", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}, timestamp=102.9)
    assert link_fast is None

    # 2. dt = 3.0s (Min bound inclusive -> HIGH)
    engine_min = SpatialTemporalCorrelationEngine(config=engine.config)
    engine_min.on_track_exit("CAM01", {"track_id": "CAM01-P1", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}, timestamp=100.0)
    link_min = engine_min.on_track_entry("CAM02", {"track_id": "CAM02-P2", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}, timestamp=103.0)
    assert link_min is not None
    assert link_min.confidence_band == "HIGH"
    assert link_min.transit_duration_seconds == 3.0

    # 3. dt = 15.0s (Max bound inclusive -> HIGH)
    engine_max = SpatialTemporalCorrelationEngine(config=engine.config)
    engine_max.on_track_exit("CAM01", {"track_id": "CAM01-P1", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}, timestamp=100.0)
    link_max = engine_max.on_track_entry("CAM02", {"track_id": "CAM02-P2", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}, timestamp=115.0)
    assert link_max is not None
    assert link_max.confidence_band == "HIGH"
    assert link_max.transit_duration_seconds == 15.0

    # 4. dt = 15.1s (Grace window -> LOW)
    engine_grace = SpatialTemporalCorrelationEngine(config=engine.config)
    engine_grace.on_track_exit("CAM01", {"track_id": "CAM01-P1", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}, timestamp=100.0)
    link_grace = engine_grace.on_track_entry("CAM02", {"track_id": "CAM02-P2", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}, timestamp=115.1)
    assert link_grace is not None
    assert link_grace.confidence_band == "LOW"
    assert link_grace.transit_duration_seconds == 15.1

    # 5. dt = 22.6s (Expired beyond grace window -> NONE)
    engine_exp = SpatialTemporalCorrelationEngine(config=engine.config)
    engine_exp.on_track_exit("CAM01", {"track_id": "CAM01-P1", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}, timestamp=100.0)
    link_exp = engine_exp.on_track_entry("CAM02", {"track_id": "CAM02-P2", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}, timestamp=122.6)
    assert link_exp is None


# ==============================================================================
# V4: Spatial Edge Mismatch & Confidence Downgrades
# ==============================================================================

def test_v4_edge_mismatch(engine):
    """
    V4: Track exits CAM-01 through top edge instead of configured right edge.
    Asserts confidence band downgrades to MEDIUM and never silently upgrades to HIGH.
    """
    t_exit = 100.0
    exit_track = {
        "track_id": "CAM01-P1",
        "object_type": "person",
        "confidence": 0.90,
        "bbox": [250, 10, 300, 45],  # Top edge (y1 <= 48)
        "trajectory": [[275, 100], [275, 50], [275, 20]]  # Moving North
    }
    window = engine.on_track_exit("CAM01", exit_track, timestamp=t_exit)
    assert window is not None
    assert window.exit_edge_matched is False  # Configured is 'right', not 'top'

    t_entry = 105.0
    entry_track = {
        "track_id": "CAM02-P2",
        "object_type": "person",
        "confidence": 0.90,
        "bbox": [10, 200, 60, 300],  # Left edge
        "trajectory": [[15, 250], [35, 250]]
    }
    link = engine.on_track_entry("CAM02", entry_track, timestamp=t_entry)
    assert link is not None
    assert link.confidence_band == "MEDIUM"  # Downgraded per V4


def test_v4_detection_confidence_downgrade(engine):
    """
    Tests detection confidence downgrade:
    Exact class match + correct edges + core timing, but CAM-02 detection confidence is 0.42 (< 0.50 threshold).
    Asserts confidence band downgrades to LOW.
    """
    t_exit = 100.0
    exit_track = {
        "track_id": "CAM01-P1",
        "object_type": "person",
        "confidence": 0.90,
        "bbox": [600, 200, 640, 300],
        "trajectory": [[520, 250], [570, 250], [610, 250]]
    }
    engine.on_track_exit("CAM01", exit_track, timestamp=t_exit)

    t_entry = 105.0
    entry_track = {
        "track_id": "CAM02-P2",
        "object_type": "person",
        "confidence": 0.42,  # Borderline confidence below 0.50
        "bbox": [10, 200, 60, 300],
        "trajectory": [[15, 250], [35, 250]]
    }
    link = engine.on_track_entry("CAM02", entry_track, timestamp=t_entry)
    assert link is not None
    assert link.confidence_band == "LOW"


# ==============================================================================
# V6: Concurrency & Disambiguation Protocol
# ==============================================================================

def test_v6_concurrency_time_closeness(engine):
    """
    V6: Two exiting tracks TA (t=100.0s) and TB (t=104.0s).
    Target entry TC appears at t=109.0s.
    Expected transit is 9.0s.
    TA delta t = 9.0s (distance 0.0s).
    TB delta t = 5.0s (distance 4.0s).
    Distance diff = 4.0s > 0.5s tie threshold.
    Asserts system links TC to TA (closest time match), consumes TA, leaves TB open.
    """
    exit_ta = {"track_id": "CAM01-TA", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}
    exit_tb = {"track_id": "CAM01-TB", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}

    win_ta = engine.on_track_exit("CAM01", exit_ta, timestamp=100.0)
    win_tb = engine.on_track_exit("CAM01", exit_tb, timestamp=104.0)

    entry_tc = {"track_id": "CAM02-TC", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}
    link = engine.on_track_entry("CAM02", entry_tc, timestamp=109.0)

    assert link is not None
    assert link.source_track_id == "CAM01-TA"
    assert link.target_track_id == "CAM02-TC"
    assert win_ta.status == WindowStatus.CONSUMED
    assert win_tb.status == WindowStatus.OPEN


def test_v6_concurrency_tie_break_decline(engine):
    """
    V6: Two exiting tracks TA (t=100.0s) and TB (t=100.2s).
    Target entry TC appears at t=109.0s.
    TA delta t = 9.0s (distance 0.0s).
    TB delta t = 8.8s (distance 0.2s).
    Distance diff = 0.2s < 0.5s tie threshold.
    Asserts system DECLINES to link rather than guessing; both windows remain OPEN.
    """
    exit_ta = {"track_id": "CAM01-TA", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}
    exit_tb = {"track_id": "CAM01-TB", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}

    win_ta = engine.on_track_exit("CAM01", exit_ta, timestamp=100.0)
    win_tb = engine.on_track_exit("CAM01", exit_tb, timestamp=100.2)

    entry_tc = {"track_id": "CAM02-TC", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}
    link = engine.on_track_entry("CAM02", entry_tc, timestamp=109.0)

    assert link is None  # Declined to link
    assert win_ta.status == WindowStatus.OPEN
    assert win_tb.status == WindowStatus.OPEN


def test_v6_concurrency_single_exit_two_entries(engine):
    """
    V6: Single exit TA at t=100.0s.
    Entry TC arrives at t=106.0s -> links to TA, consumes window.
    Entry TD arrives at t=107.0s -> no open window remaining -> unlinked stand-alone event.
    """
    exit_ta = {"track_id": "CAM01-TA", "object_type": "person", "confidence": 0.9, "bbox": [600, 200, 640, 300]}
    win_ta = engine.on_track_exit("CAM01", exit_ta, timestamp=100.0)

    entry_tc = {"track_id": "CAM02-TC", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}
    link_tc = engine.on_track_entry("CAM02", entry_tc, timestamp=106.0)
    assert link_tc is not None
    assert link_tc.target_track_id == "CAM02-TC"
    assert win_ta.status == WindowStatus.CONSUMED

    entry_td = {"track_id": "CAM02-TD", "object_type": "person", "confidence": 0.9, "bbox": [10, 200, 50, 300]}
    link_td = engine.on_track_entry("CAM02", entry_td, timestamp=107.0)
    assert link_td is None  # Cannot double-link consumed window


# ==============================================================================
# V7: Garbage Collection & Memory Bounding
# ==============================================================================

def test_v7_garbage_collection_cleanup(engine):
    """
    V7: Inject 1,000 synthetic exits on CAM-01 across timestamps t=0 to t=1000 with 0 entries on CAM-02.
    Advance time to t=1100.0s.
    Asserts all 1,000 expired windows are purged by GC, memory stays bounded, zero unbounded growth.
    """
    for i in range(1000):
        t_exit = float(i)
        track = {
            "track_id": f"CAM01-SYN-{i}",
            "object_type": "person",
            "confidence": 0.9,
            "bbox": [600, 200, 640, 300]
        }
        # Note: circuit breaker max_active_windows will also manage memory
        engine.on_track_exit("CAM01", track, timestamp=t_exit)

    # Current active windows is bounded by max_active_windows (200)
    assert len(engine.active_windows) <= 200

    # Advance time past all windows and trigger GC
    purged_count = engine.cleanup_expired(current_timestamp=2000.0)
    assert len(engine.active_windows) == 0
    assert engine.metrics["total_expired"] >= 1000
```

---

## 5. Verification Method

To independently verify the Milestone 1 deliverables upon implementation:

1. **Unit Test Execution**:
   Run pytest against the unit test suite:
   ```bash
   pytest tests/unit/test_correlation_engine.py -v
   ```
   **Success Criteria**: All 8 unit test methods (`test_v1_positive_match`, `test_v2_class_mismatch`, `test_v3_timing_boundaries`, `test_v4_edge_mismatch`, `test_v4_detection_confidence_downgrade`, `test_v6_concurrency_time_closeness`, `test_v6_concurrency_tie_break_decline`, `test_v6_concurrency_single_exit_two_entries`, `test_v7_garbage_collection_cleanup`) pass with 100% success rate.

2. **Configuration Validation**:
   Validate that `configs/adjacency.yaml` loads and validates cleanly through `AdjacencyRootConfig.model_validate(yaml.safe_load(f))`.

3. **No Appearance-Embedding Code Invariant**:
   Inspect `intelligence/boundary.py` and `intelligence/correlation.py` to confirm zero imports of `botsort`, `deep_sort`, `torchvision`, `osnet`, `reid`, or visual feature extractors.

4. **Prohibited Terminology Check**:
   Search `intelligence/boundary.py` and `intelligence/correlation.py` for prohibited terms (`confirmed identity`, `same person`, `biometric match`) to ensure complete compliance.
