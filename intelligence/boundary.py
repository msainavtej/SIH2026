"""
intelligence/boundary.py

Spatial Edge Boundary Detection and Trajectory Velocity Analyzer.
Evaluates bounding box spatial proximity to image edges and computes directional
velocity vectors without using appearance embeddings.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


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
        default_frame_size: Tuple[int, int] = (640, 480),
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
        frame_size: Optional[Tuple[int, int]] = None,
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
        edge_clean = edge.lower().strip()
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        dx_thresh = w * self.edge_threshold_fraction
        dy_thresh = h * self.edge_threshold_fraction

        if edge_clean == "right":
            return x2 >= (w - dx_thresh) or cx >= (w - dx_thresh)
        elif edge_clean == "left":
            return x1 <= dx_thresh or cx <= dx_thresh
        elif edge_clean == "top":
            return y1 <= dy_thresh or cy <= dy_thresh
        elif edge_clean == "bottom":
            return y2 >= (h - dy_thresh) or cy >= (h - dy_thresh)
        return False

    def detect_closest_edge(
        self,
        bbox: List[int],
        frame_size: Optional[Tuple[int, int]] = None,
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
        mode: Literal["exit", "entry"] = "exit",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Computes directional displacement vector from trajectory history.

        :param trajectory: List of [x, y] coordinates in chronological order.
        :param edge: "left", "right", "top", "bottom"
        :param mode: "exit" (moving towards/out of edge) or "entry" (moving away/in from edge).
        :return: (vector_matched, metadata_dict)
        """
        edge_clean = edge.lower().strip()
        if not trajectory or len(trajectory) < self.min_trajectory_points:
            # Insufficient points: for entry, newly appearing object may only have 1-2 points
            if mode == "entry":
                return True, {
                    "reason": "insufficient_points_entry_permissive",
                    "point_count": len(trajectory) if trajectory else 0,
                }
            return False, {
                "reason": "insufficient_points_exit",
                "point_count": len(trajectory) if trajectory else 0,
            }

        # Calculate displacement from oldest relevant point to newest point
        p_start = trajectory[0]
        p_end = trajectory[-1]
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]  # Note: screen coords Y increases downwards

        matched = False
        if mode == "exit":
            if edge_clean == "right":
                matched = dx > 0 and abs(dx) >= abs(dy) * 0.5  # Moving eastward
            elif edge_clean == "left":
                matched = dx < 0 and abs(dx) >= abs(dy) * 0.5  # Moving westward
            elif edge_clean == "top":
                matched = dy < 0 and abs(dy) >= abs(dx) * 0.5  # Moving northward (up)
            elif edge_clean == "bottom":
                matched = dy > 0 and abs(dy) >= abs(dx) * 0.5  # Moving southward (down)
        else:  # mode == "entry"
            if edge_clean == "right":
                matched = dx < 0  # Entered right edge, moving inward (westward)
            elif edge_clean == "left":
                matched = dx > 0  # Entered left edge, moving inward (eastward)
            elif edge_clean == "top":
                matched = dy > 0  # Entered top edge, moving inward (southward)
            elif edge_clean == "bottom":
                matched = dy < 0  # Entered bottom edge, moving inward (northward)

        meta = {
            "dx": dx,
            "dy": dy,
            "mode": mode,
            "edge": edge_clean,
            "point_count": len(trajectory),
            "matched": matched,
        }
        return matched, meta

    def evaluate_edge_crossing(
        self,
        bbox: List[int],
        trajectory: List[List[int]],
        configured_edge: str,
        frame_size: Optional[Tuple[int, int]] = None,
        mode: Literal["exit", "entry"] = "exit",
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
        configured_edge_clean = configured_edge.lower().strip()
        prox_matched = self.check_edge_proximity(bbox, configured_edge_clean, frame_size)
        detected_edge = self.detect_closest_edge(bbox, frame_size)
        vec_matched, vec_meta = self.check_trajectory_vector(trajectory, configured_edge_clean, mode=mode)

        is_valid = prox_matched and (
            vec_matched or (mode == "entry" and (not trajectory or len(trajectory) < self.min_trajectory_points))
        )

        return EdgeEvaluationResult(
            proximity_matched=prox_matched,
            vector_matched=vec_matched,
            configured_edge=configured_edge_clean,
            detected_edge=detected_edge,
            is_valid=is_valid,
            details={
                "proximity_matched": prox_matched,
                "vector_matched": vec_matched,
                "vector_meta": vec_meta,
                "detected_edge": detected_edge,
                "configured_edge": configured_edge_clean,
                "mode": mode,
            },
        )


class SpatialEdgeAnalyzer:
    """
    Adapter analyzer class conforming to track-level edge evaluation interface.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        edge_fraction: float = 0.10,
        min_trajectory_points: int = 3,
    ):
        self.width = width
        self.height = height
        self.edge_fraction = edge_fraction
        self.analyzer = SpatialBoundaryAnalyzer(
            edge_threshold_fraction=edge_fraction,
            min_trajectory_points=min_trajectory_points,
            default_frame_size=(width, height),
        )

    def is_exit_edge_matched(self, track: Dict[str, Any], configured_edge: str) -> bool:
        bbox = track.get("bbox", [])
        trajectory = track.get("trajectory", [])
        res = self.analyzer.evaluate_edge_crossing(
            bbox,
            trajectory,
            configured_edge,
            frame_size=(self.width, self.height),
            mode="exit",
        )
        return res.proximity_matched

    def is_entry_edge_matched(self, track: Dict[str, Any], configured_edge: str) -> bool:
        bbox = track.get("bbox", [])
        trajectory = track.get("trajectory", [])
        res = self.analyzer.evaluate_edge_crossing(
            bbox,
            trajectory,
            configured_edge,
            frame_size=(self.width, self.height),
            mode="entry",
        )
        return res.proximity_matched


def detect_edge_transition(
    bbox: List[int],
    trajectory: Optional[List[List[int]]] = None,
    width: int = 640,
    height: int = 480,
    edge_fraction: float = 0.10,
) -> Optional[str]:
    """Helper to detect closest boundary edge for a bounding box."""
    analyzer = SpatialBoundaryAnalyzer(
        edge_threshold_fraction=edge_fraction,
        default_frame_size=(width, height),
    )
    return analyzer.detect_closest_edge(bbox, frame_size=(width, height))


def evaluate_exit_edge(
    track: Dict[str, Any],
    configured_edge: str,
    width: int = 640,
    height: int = 480,
    edge_fraction: float = 0.10,
) -> EdgeEvaluationResult:
    """Helper to evaluate exit edge crossing for a track dictionary."""
    analyzer = SpatialBoundaryAnalyzer(
        edge_threshold_fraction=edge_fraction,
        default_frame_size=(width, height),
    )
    return analyzer.evaluate_edge_crossing(
        bbox=track.get("bbox", []),
        trajectory=track.get("trajectory", []),
        configured_edge=configured_edge,
        frame_size=(width, height),
        mode="exit",
    )


def evaluate_entry_edge(
    track: Dict[str, Any],
    configured_edge: str,
    width: int = 640,
    height: int = 480,
    edge_fraction: float = 0.10,
) -> EdgeEvaluationResult:
    """Helper to evaluate entry edge crossing for a track dictionary."""
    analyzer = SpatialBoundaryAnalyzer(
        edge_threshold_fraction=edge_fraction,
        default_frame_size=(width, height),
    )
    return analyzer.evaluate_edge_crossing(
        bbox=track.get("bbox", []),
        trajectory=track.get("trajectory", []),
        configured_edge=configured_edge,
        frame_size=(width, height),
        mode="entry",
    )
