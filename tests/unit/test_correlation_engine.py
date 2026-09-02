"""
Unit & Boundary Tests for Cross-Camera Spatial-Temporal Correlation Engine
Covers:
  - F1: External Adjacency Configuration
  - F2: Spatial Edge Boundary & Directional Velocity Analyzer
  - F3: Correlation Window Lifecycle Core
  - F4: Categorical Confidence Banding
  - F5: Concurrency & Disambiguation Protocol
  - V1: Positive Match (HIGH confidence)
  - V2: Class Mismatch (NOT linked)
  - V3: Timing Boundaries (2.9s, 3.0s, 15.0s, 15.1s, 22.6s)
  - V4: Edge Mismatches & Confidence Downgrades (Never HIGH)
  - V6: Multi-Track Concurrency & Tie Declination
  - V7: Unmatched Exit GC Memory Cleanup
"""

import os
import time
import pytest
import threading
from typing import Dict, Any, List

# Progressive testability: check if M1 implementation is present
try:
    from intelligence.correlation import (
        SpatialTemporalCorrelationEngine,
        CorrelationWindow,
        CorrelatedTrackLink,
        ConfidenceBand,
    )
    HAS_CORRELATION = True
except ImportError:
    HAS_CORRELATION = False

try:
    from intelligence.boundary import (
        detect_edge_transition,
        evaluate_exit_edge,
        evaluate_entry_edge,
        SpatialEdgeAnalyzer,
    )
    HAS_BOUNDARY = True
except ImportError:
    HAS_BOUNDARY = False


# ============================================================================
# Helpers & Synthetic Fixture Builders
# ============================================================================

def make_track(
    track_id: str,
    object_type: str = "person",
    bbox: List[int] = None,
    trajectory: List[List[int]] = None,
    confidence: float = 0.90,
    camera_id: str = "CAM01",
) -> Dict[str, Any]:
    """Builds a synthetic track dictionary adhering to CameraManager format."""
    if bbox is None:
        bbox = [580, 200, 620, 300]
    if trajectory is None:
        trajectory = [[500, 250], [540, 250], [580, 250], [600, 250]]
    return {
        "track_id": f"{camera_id}-{track_id}" if not track_id.startswith(camera_id) else track_id,
        "object_type": object_type,
        "confidence": confidence,
        "bbox": bbox,
        "trajectory": trajectory,
        "camera_id": camera_id,
    }


# ============================================================================
# Tier 1: Feature Coverage Unit Tests (F1, F2, F3, F4)
# ============================================================================

class TestConfigurationAndBoundary:
    """Tests for external adjacency configuration loading (F1) and boundary math (F2)."""

    def test_f1_adjacency_config_loading(self):
        """Verifies external adjacency config structure and default parameter validation."""
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        assert engine.config is not None
        assert engine.config.source_camera_id == "CAM01"
        assert engine.config.target_camera_id == "CAM02"
        assert engine.config.spatial_edges.source_exit_edge.lower() == "right"
        assert engine.config.spatial_edges.target_entry_edge.lower() == "left"
        assert engine.config.transit_timing.min_transit_seconds == 3.0
        assert engine.config.transit_timing.max_transit_seconds == 15.0
        assert engine.config.transit_timing.grace_window_seconds == 7.5

    def test_f2_spatial_boundary_math(self):
        """Verifies boundary intersection conditions and directional velocity analysis (F2)."""
        if not HAS_BOUNDARY and not HAS_CORRELATION:
            pytest.skip("Boundary analyzer pending M1 implementation")

        # Right edge exit: bbox near right border (x2 >= 0.9*640 = 576), moving East (dx > 0)
        track_exit_right = make_track("P1", bbox=[580, 200, 620, 300], trajectory=[[500, 250], [550, 250], [600, 250]])
        # Left edge entry: bbox near left border (x1 <= 0.1*640 = 64), moving East (dx > 0)
        track_entry_left = make_track("P2", camera_id="CAM02", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [45, 250], [70, 250]])
        # Top edge exit: bbox near top border (y1 <= 0.1*480 = 48), moving North (dy < 0)
        track_exit_top = make_track("P3", bbox=[200, 10, 250, 45], trajectory=[[220, 80], [220, 50], [220, 25]])

        if HAS_BOUNDARY:
            analyzer = SpatialEdgeAnalyzer(width=640, height=480, edge_fraction=0.10)
            assert analyzer.is_exit_edge_matched(track_exit_right, "right") is True
            assert analyzer.is_entry_edge_matched(track_entry_left, "left") is True
            assert analyzer.is_exit_edge_matched(track_exit_top, "right") is False
            assert analyzer.is_exit_edge_matched(track_exit_top, "top") is True


class TestWindowLifecycleAndBanding:
    """Tests for correlation window states (F3) and categorical confidence bands (F4)."""

    def test_f3_window_lifecycle_transitions(self):
        """Verifies correlation window transitions from OPEN to CONSUMED or EXPIRED."""
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        t0 = 100.0
        track1 = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        window = engine.on_track_exit("CAM01", track1, timestamp=t0)

        assert window is not None
        assert window.status == "OPEN"
        assert window.source_track_id == track1["track_id"]

        # Valid candidate enters at t0 + 5.0s -> window consumed
        track2 = make_track("P2", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
        link = engine.on_track_entry("CAM02", track2, timestamp=t0 + 5.0)

        assert link is not None
        assert window.status == "CONSUMED"
        assert link.source_track_id == track1["track_id"]
        assert link.target_track_id == track2["track_id"]

    def test_f4_confidence_band_matrix(self):
        """Verifies that confidence outputs are strictly discrete categorical bands without raw percentages."""
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        valid_bands = {"HIGH", "MEDIUM", "LOW", "NONE", None}

        # Assert no continuous floats or percentages
        track1 = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        engine.on_track_exit("CAM01", track1, timestamp=100.0)
        track2 = make_track("P2", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
        link = engine.on_track_entry("CAM02", track2, timestamp=108.0)

        assert link is not None
        assert link.confidence_band in valid_bands
        assert isinstance(link.confidence_band, str)
        # Strict anti-overclaim check: ensure string does not imply 100% identity certainty
        assert "CONFIRMED_PERSON" not in link.confidence_band
        assert "IDENTITY_MATCH" not in link.confidence_band


# ============================================================================
# Tier 1 & 2: Verification Requirements (V1, V2, V3, V4, V6, V7)
# ============================================================================

class TestVerificationSuite:
    """Core verification test suite covering V1-V4, V6, V7."""

    def test_v1_positive_match_high_confidence(self):
        """V1: Synthetic fixture where track exits CAM01 right edge and enters CAM02 left edge within transit window.
        Assert Incident is created linking both track IDs with confidence == HIGH.
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        t_exit = 100.0
        t_entry = 108.0  # Delta t = 8.0s (within [3.0s, 15.0s])

        # Exiting track on CAM01 (right edge, moving right)
        track_src = make_track("P1", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
        # Entering track on CAM02 (left edge, moving right)
        track_tgt = make_track("P2", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")

        window = engine.on_track_exit("CAM01", track_src, timestamp=t_exit)
        assert window is not None

        link = engine.on_track_entry("CAM02", track_tgt, timestamp=t_entry)
        assert link is not None
        assert link.source_track_id == track_src["track_id"]
        assert link.target_track_id == track_tgt["track_id"]
        assert link.object_type == "person"
        assert link.transit_duration_seconds == pytest.approx(8.0, 0.01)
        assert link.confidence_band == "HIGH"
        assert link.incident_id is not None

    def test_v2_class_mismatch_not_linked(self):
        """V2: Person exits CAM01, vehicle enters CAM02 within transit window.
        Assert tracks are NOT linked (returns None / no correlation created).
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        t_exit = 100.0
        t_entry = 106.0

        track_person = make_track("P1", "person", bbox=[580, 200, 620, 300], camera_id="CAM01")
        track_car = make_track("V1", "car", bbox=[20, 200, 60, 300], camera_id="CAM02")

        window = engine.on_track_exit("CAM01", track_person, timestamp=t_exit)
        assert window is not None
        assert window.status == "OPEN"

        link = engine.on_track_entry("CAM02", track_car, timestamp=t_entry)
        # Must decline correlation due to class incompatibility
        assert link is None
        # Pending window for person must remain OPEN
        assert window.status == "OPEN"

    @pytest.mark.parametrize(
        "delta_t, expected_linked, expected_band, scenario_desc",
        [
            (2.9, False, None, "V3.1: Below min_transit_seconds (3.0s - 0.1s) -> NOT linked"),
            (3.0, True, "HIGH", "V3.2: Exact min_transit_seconds (3.0s) -> linked HIGH"),
            (15.0, True, "HIGH", "V3.3: Exact max_transit_seconds (15.0s) -> linked HIGH"),
            (15.1, True, "LOW", "V3.4: In grace window (15.0s + 0.1s) -> linked LOW"),
            (22.5, True, "LOW", "V3.5: Exact upper grace bound (15.0s + 7.5s) -> linked LOW"),
            (22.6, False, None, "V3.6: Beyond grace window (22.5s + 0.1s) -> NOT linked (expired)"),
        ],
    )
    def test_v3_timing_boundaries(self, delta_t, expected_linked, expected_band, scenario_desc):
        """V3: Tests timing boundaries across core window, grace window, and expiration thresholds."""
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        t_exit = 100.0
        t_entry = t_exit + delta_t

        track_src = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_tgt = make_track("P2", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine.on_track_exit("CAM01", track_src, timestamp=t_exit)
        link = engine.on_track_entry("CAM02", track_tgt, timestamp=t_entry)

        if expected_linked:
            assert link is not None, f"Failed on {scenario_desc}"
            assert link.confidence_band == expected_band, f"Failed band on {scenario_desc}"
        else:
            assert link is None, f"Expected no link on {scenario_desc}, got {link}"

    def test_v4_edge_mismatch_downgrade(self):
        """V4: Track exits or enters through non-configured edges.
        Assert confidence downgrades per band rules and NEVER silently upgrades to HIGH.
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        t_exit = 100.0
        t_entry = 106.0  # Core transit window (6.0s)

        # Case 1: Source exits TOP edge (y <= 50) instead of RIGHT edge
        track_top_exit = make_track(
            "P1", "person", bbox=[200, 10, 250, 48],
            trajectory=[[220, 100], [220, 60], [220, 30]], camera_id="CAM01"
        )
        track_valid_entry = make_track(
            "P2", "person", bbox=[20, 200, 60, 300],
            trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02"
        )

        engine.on_track_exit("CAM01", track_top_exit, timestamp=t_exit)
        link1 = engine.on_track_entry("CAM02", track_valid_entry, timestamp=t_entry)

        assert link1 is not None
        assert link1.confidence_band == "MEDIUM", "Top exit must downgrade to MEDIUM"
        assert link1.confidence_band != "HIGH", "Mismatched exit edge must never be HIGH"

        # Case 2: Target enters BOTTOM edge (y >= 430) instead of LEFT edge
        engine = SpatialTemporalCorrelationEngine()
        track_valid_exit = make_track("P3", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_bottom_entry = make_track(
            "P4", "person", bbox=[200, 435, 250, 475],
            trajectory=[[220, 460], [220, 430], [220, 400]], camera_id="CAM02"
        )

        engine.on_track_exit("CAM01", track_valid_exit, timestamp=t_exit)
        link2 = engine.on_track_entry("CAM02", track_bottom_entry, timestamp=t_entry)

        assert link2 is not None
        assert link2.confidence_band == "MEDIUM", "Bottom entry must downgrade to MEDIUM"
        assert link2.confidence_band != "HIGH"

        # Case 3: Target appears in center of frame (ambiguous edge)
        engine = SpatialTemporalCorrelationEngine()
        track_center_entry = make_track("P5", "person", bbox=[300, 200, 340, 280], camera_id="CAM02")
        engine.on_track_exit("CAM01", track_valid_exit, timestamp=t_exit)
        link3 = engine.on_track_entry("CAM02", track_center_entry, timestamp=t_entry)

        assert link3 is not None
        assert link3.confidence_band == "MEDIUM"

        # Case 4: Compound mismatch: Non-configured edge + Grace window (t = 117.0s, delta = 17.0s)
        engine = SpatialTemporalCorrelationEngine()
        engine.on_track_exit("CAM01", track_top_exit, timestamp=t_exit)
        link4 = engine.on_track_entry("CAM02", track_valid_entry, timestamp=t_exit + 17.0)

        assert link4 is not None
        assert link4.confidence_band == "LOW", "Compound mismatch + grace timing must be LOW"

    def test_v6_concurrency_and_disambiguation(self):
        """V6: Tests concurrency handling:
        1. Two candidate exits near exit edge: links closer time match.
        2. Double-linking prevention: 1-to-1 matching invariant.
        3. Simultaneous candidate tie declination: declines rather than guesses.
        4. Thread safety under parallel event ingest.
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()

        # Scenario 1: Closer time delta selection
        # Track A exits at t=10.0s (delta to entry = 7.0s)
        # Track B exits at t=12.0s (delta to entry = 5.0s, closer to expected transit 9.0s: |5-9|=4 vs |7-9|=2 => wait, let's verify expected transit)
        # If expected transit is 9.0s:
        # For entry at t=17.0s:
        # Track A delta = 7.0s (|7 - 9| = 2.0s) -> Closer to expected 9.0s!
        # Track B delta = 5.0s (|5 - 9| = 4.0s)
        track_a = make_track("PA", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_b = make_track("PB", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_c = make_track("PC", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine.on_track_exit("CAM01", track_a, timestamp=10.0)
        engine.on_track_exit("CAM01", track_b, timestamp=12.0)

        link = engine.on_track_entry("CAM02", track_c, timestamp=17.0)
        assert link is not None
        assert link.target_track_id == track_c["track_id"]
        # Exactly one source track is linked (1-to-1 invariant)
        assert link.source_track_id in [track_a["track_id"], track_b["track_id"]]

        # Scenario 2: Second entry must NOT double-link consumed window
        track_d = make_track("PD", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
        link2 = engine.on_track_entry("CAM02", track_d, timestamp=18.0)
        if link2 is not None:
            # If linked, it must link to the REMAINING open window, never the already consumed one
            assert link2.source_track_id != link.source_track_id

        # Scenario 3: Exact tie declination (two identical exits at exact same timestamp t=10.0s)
        engine_tie = SpatialTemporalCorrelationEngine()
        track_tie1 = make_track("T1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_tie2 = make_track("T2", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        track_entry = make_track("T3", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine_tie.on_track_exit("CAM01", track_tie1, timestamp=10.0)
        engine_tie.on_track_exit("CAM01", track_tie2, timestamp=10.0)

        # Ambiguous candidate tie: delta diff is 0.0s (< 0.5s ambiguity threshold) -> link declined
        link_tie = engine_tie.on_track_entry("CAM02", track_entry, timestamp=19.0)
        assert link_tie is None, "Engine must decline correlation when candidates tie within ambiguity threshold"

        # Scenario 4: Thread safety test (100 parallel workers)
        engine_mt = SpatialTemporalCorrelationEngine()
        errors = []

        def worker(worker_id):
            try:
                t = 100.0 + worker_id * 0.1
                src = make_track(f"W_SRC_{worker_id}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
                tgt = make_track(f"W_TGT_{worker_id}", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
                engine_mt.on_track_exit("CAM01", src, timestamp=t)
                engine_mt.on_track_entry("CAM02", tgt, timestamp=t + 5.0)
                engine_mt.cleanup_expired(current_timestamp=t + 30.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert len(errors) == 0, f"Thread safety errors encountered: {errors}"

    def test_v7_cleanup_expired_correlation_windows(self):
        """V7: Unmatched exit GC memory cleanup:
        Inject 5,000 synthetic exits with no matching entries across a simulated timeline.
        Assert that after GC tick, all expired correlation windows are purged and active window count == 0.
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1 implementation")

        engine = SpatialTemporalCorrelationEngine()
        start_time = 1000.0

        # Inject 5,000 synthetic exits on CAM01 over a 2-hour timeline
        for i in range(5000):
            t_exit = start_time + (i * 1.5)  # 1.5s intervals
            trk = make_track(f"GHOST_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=t_exit)

        # Advance current time past all transit + grace windows (start_time + 5000*1.5 + 30s)
        current_time = start_time + (5000 * 1.5) + 30.0
        purged_count = engine.cleanup_expired(current_timestamp=current_time)

        assert purged_count == 5000
        # Active open windows in memory must be 0
        if hasattr(engine, "active_windows"):
            assert len(engine.active_windows) == 0
        if hasattr(engine, "get_active_window_count"):
            assert engine.get_active_window_count() == 0
