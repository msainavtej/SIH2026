"""
intelligence/correlation.py

Cross-Camera Spatial-Temporal Correlation Engine.
Links track segments across adjacent cameras using external YAML configuration,
bounding box spatial vectors, and temporal transit windows without appearance embeddings.
"""

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, model_validator

from intelligence.boundary import EdgeEvaluationResult, SpatialBoundaryAnalyzer


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
    max_active_windows: int = Field(default=10000, ge=1)


class AdjacencyPairConfig(BaseModel):
    pair_id: str = "ADJ_CAM01_CAM02"
    enabled: bool = True
    source_camera_id: str = "CAM01"
    target_camera_id: str = "CAM02"
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
    edge_match_status: str  # "BOTH_MATCHED", "SOURCE_MATCHED_TARGET_AMBIGUOUS", etc.
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
        config: Optional[AdjacencyPairConfig] = None,
    ):
        self._lock = threading.RLock()

        if config is not None:
            self.config = config
        elif config_path and os.path.exists(config_path):
            self.config = self.load_config(config_path)
        else:
            # Fallback default configuration
            self.config = AdjacencyPairConfig(
                pair_id="ADJ_CAM01_CAM02",
                source_camera_id="CAM01",
                target_camera_id="CAM02",
            )

        self.boundary_analyzer = SpatialBoundaryAnalyzer(
            edge_threshold_fraction=self.config.spatial_edges.edge_threshold_fraction,
            min_trajectory_points=self.config.spatial_edges.min_trajectory_points,
        )

        self.active_windows: Dict[str, CorrelationWindow] = {}
        self.last_gc_time: float = 0.0

        # Operational metrics
        self.metrics: Dict[str, int] = {
            "total_windows_opened": 0,
            "total_correlated": 0,
            "total_expired": 0,
            "total_declined_ties": 0,
            "total_class_mismatches": 0,
            "total_timing_rejections": 0,
        }

    @staticmethod
    def load_config(config_path: str) -> AdjacencyPairConfig:
        """Load and validate external YAML configuration."""
        try:
            with open(config_path, "r") as f:
                raw_yaml = yaml.safe_load(f)
            root = AdjacencyRootConfig.model_validate(raw_yaml)
            return root.adjacency_map
        except Exception as e:
            print(f"Failed to load adjacency config from {config_path}: {e}. Disabling correlation.")
            return AdjacencyPairConfig(
                pair_id="ADJ_DISABLED",
                source_camera_id="DISABLED",
                target_camera_id="DISABLED",
                enabled=False
            )

    def get_active_window_count(self) -> int:
        """Returns the count of currently OPEN correlation windows."""
        with self._lock:
            return sum(1 for w in self.active_windows.values() if w.status == WindowStatus.OPEN)

    def on_track_exit(
        self,
        camera_id: str,
        track: Dict[str, Any],
        timestamp: Optional[float] = None,
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

        t_now = float(timestamp) if timestamp is not None else time.time()

        with self._lock:
            # Circuit breaker memory cap
            if len(self.active_windows) >= self.config.lifecycle.max_active_windows:
                self.cleanup_expired(t_now)
                if len(self.active_windows) >= self.config.lifecycle.max_active_windows:
                    # Evict oldest window to protect memory bounds
                    oldest_key = min(
                        self.active_windows.keys(),
                        key=lambda k: self.active_windows[k].exit_timestamp,
                    )
                    del self.active_windows[oldest_key]
                    self.metrics["total_expired"] += 1

            bbox = track.get("bbox", [0, 0, 0, 0])
            trajectory = track.get("trajectory", [])
            edge_eval = self.boundary_analyzer.evaluate_edge_crossing(
                bbox=bbox,
                trajectory=trajectory,
                configured_edge=self.config.spatial_edges.source_exit_edge,
                mode="exit",
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
                status=WindowStatus.OPEN,
            )

            self.active_windows[window_id] = window
            self.metrics["total_windows_opened"] += 1
            return window

    def on_track_entry(
        self,
        camera_id: str,
        track: Dict[str, Any],
        timestamp: Optional[float] = None,
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

        t_now = float(timestamp) if timestamp is not None else time.time()

        with self._lock:
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
                    # Ambiguous tie: decline to link rather than guessing (Rule V6)
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
        entry_timestamp: float,
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
            mode="entry",
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
            target_entry_time=entry_timestamp,
        )

    def cleanup_expired(self, current_timestamp: float) -> int:
        """
        Purges expired correlation windows beyond t_exit + max_transit + grace_window.
        Guarantees bounded memory with zero unbounded growth (Rule V7).

        :param current_timestamp: Current epoch timestamp in seconds.
        :return: Count of purged windows in this invocation.
        """
        with self._lock:
            self.last_gc_time = current_timestamp
            max_t = self.config.transit_timing.max_transit_seconds
            grace_t = self.config.transit_timing.grace_window_seconds
            cutoff_duration = max_t + grace_t

            keys_to_purge: List[str] = []
            for win_id, win in list(self.active_windows.items()):
                age = current_timestamp - win.exit_timestamp
                if win.status == WindowStatus.CONSUMED:
                    if age > cutoff_duration:
                        keys_to_purge.append(win_id)
                elif age > cutoff_duration:
                    win.status = WindowStatus.EXPIRED
                    keys_to_purge.append(win_id)

            for win_id in keys_to_purge:
                del self.active_windows[win_id]
                self.metrics["total_expired"] += 1

            return len(keys_to_purge)
