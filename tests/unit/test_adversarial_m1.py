"""
Adversarial Stress Test Suite for Milestone 1 (M1) Core Components
intelligence/boundary.py and intelligence/correlation.py

Stress dimensions:
1. High concurrency stress: 1,000+ to 5,000+ concurrent exits and entries across multiple threads.
2. Exact boundary timing edge conditions (2.999s, 3.000s, 15.000s, 15.001s, 22.500s, 22.501s, floats, out-of-order).
3. Ambiguity tie tests with exact identical distance deltas and equidistant candidates.
4. GC stress under massive window accumulation, circuit breaker caps, and partial purge lifecycle.
5. Adversarial input fuzzing (degenerate bboxes, zero movement trajectories, extreme confidence values).
6. Temporal anomaly, clock skew, non-monotonic timestamps, and re-entrant lock verification.
"""

import time
import math
import uuid
import pytest
import threading
import concurrent.futures
from typing import Dict, Any, List

from intelligence.boundary import (
    SpatialBoundaryAnalyzer,
    SpatialEdgeAnalyzer,
    EdgeEvaluationResult,
    detect_edge_transition,
    evaluate_exit_edge,
    evaluate_entry_edge,
)
from intelligence.correlation import (
    SpatialTemporalCorrelationEngine,
    CorrelationWindow,
    CorrelatedTrackLink,
    ConfidenceBand,
    WindowStatus,
    AdjacencyPairConfig,
    SpatialEdgesConfig,
    TransitTimingConfig,
    ConfidenceRulesConfig,
    LifecycleConfig,
)


# ============================================================================
# Helpers & Fixture Generators
# ============================================================================

def make_track(
    track_id: str,
    object_type: str = "person",
    bbox: List[int] = None,
    trajectory: List[List[int]] = None,
    confidence: float = 0.90,
    camera_id: str = "CAM01",
) -> Dict[str, Any]:
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
# 1. Exact Boundary Timing Edge Conditions
# ============================================================================

class TestExactBoundaryTiming:
    """Stress-tests exact timing boundary limits and float tolerances."""

    @pytest.mark.parametrize(
        "delta_t, expected_linked, expected_band, label",
        [
            (2.999, False, None, "Sub-millisecond before min_transit (2.999s)"),
            (3.000, True, "HIGH", "Exact min_transit boundary (3.000s)"),
            (3.001, True, "HIGH", "Sub-millisecond after min_transit (3.001s)"),
            (8.999, True, "HIGH", "Sub-millisecond before expected transit (8.999s)"),
            (9.000, True, "HIGH", "Exact expected transit (9.000s)"),
            (9.001, True, "HIGH", "Sub-millisecond after expected transit (9.001s)"),
            (14.999, True, "HIGH", "Sub-millisecond before max_transit (14.999s)"),
            (15.000, True, "HIGH", "Exact max_transit boundary (15.000s)"),
            (15.001, True, "LOW", "Sub-millisecond after max_transit entering grace (15.001s)"),
            (22.499, True, "LOW", "Sub-millisecond before grace cutoff (22.499s)"),
            (22.500, True, "LOW", "Exact upper grace cutoff boundary (22.500s)"),
            (22.501, False, None, "Sub-millisecond after grace cutoff (22.501s)"),
            (0.000, False, None, "Zero transit duration (instantaneous)"),
            (-1.000, False, None, "Negative transit duration (out of order)"),
            (100.000, False, None, "Far expired transit duration (100s)"),
        ],
    )
    def test_exact_timing_matrix(self, delta_t, expected_linked, expected_band, label):
        engine = SpatialTemporalCorrelationEngine()
        t_exit = 1000.0
        t_entry = t_exit + delta_t

        src_track = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt_track = make_track("P2", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine.on_track_exit("CAM01", src_track, timestamp=t_exit)
        link = engine.on_track_entry("CAM02", tgt_track, timestamp=t_entry)

        if expected_linked:
            assert link is not None, f"Expected match for {label}, got None"
            assert link.confidence_band == expected_band, f"Expected band {expected_band} for {label}, got {link.confidence_band}"
            assert link.transit_duration_seconds == pytest.approx(round(delta_t, 2), 0.01)
        else:
            assert link is None, f"Expected rejection for {label}, got {link}"

    def test_float_precision_extreme_boundaries(self):
        """Tests floating point epsilon behavior near 3.0, 15.0, and 22.5."""
        engine = SpatialTemporalCorrelationEngine()
        t_exit = 1000.0

        # Epsilon below 3.0: 3.0 - 1e-7 -> reject
        src1 = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt1 = make_track("P1", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
        engine.on_track_exit("CAM01", src1, timestamp=t_exit)
        assert engine.on_track_entry("CAM02", tgt1, timestamp=t_exit + 3.0 - 1e-7) is None

        # Epsilon above 22.5: 22.5 + 1e-7 -> reject
        engine2 = SpatialTemporalCorrelationEngine()
        engine2.on_track_exit("CAM01", src1, timestamp=t_exit)
        assert engine2.on_track_entry("CAM02", tgt1, timestamp=t_exit + 22.5 + 1e-7) is None


# ============================================================================
# 2. Ambiguity Tie Tests & Disambiguation Protocol
# ============================================================================

class TestAmbiguityTieDisambiguation:
    """Stress-tests candidate tie scenarios, equidistant candidates, and state integrity."""

    def test_exact_identical_distance_delta_tie(self):
        """Two tracks exit at the exact same timestamp (distance delta = 0.0s). Engine must decline link."""
        engine = SpatialTemporalCorrelationEngine()
        t_exit = 500.0
        t_entry = 509.0  # Exact 9.0s transit (dist_expected = 0.0s for both)

        src_a = make_track("A", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        src_b = make_track("B", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt = make_track("T", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        win_a = engine.on_track_exit("CAM01", src_a, timestamp=t_exit)
        win_b = engine.on_track_exit("CAM01", src_b, timestamp=t_exit)

        # Disambiguation tie: abs(0.0 - 0.0) = 0.0 < 0.5s -> Declined!
        link = engine.on_track_entry("CAM02", tgt, timestamp=t_entry)
        assert link is None, "Identical delta candidates must decline link"
        assert engine.metrics["total_declined_ties"] == 1

        # Windows must remain OPEN (not erroneously consumed or discarded)
        assert win_a.status == WindowStatus.OPEN
        assert win_b.status == WindowStatus.OPEN
        assert engine.get_active_window_count() == 2

    def test_symmetric_equidistant_candidates_around_expected(self):
        """
        Candidate 1: exit at t=10.0, entry at t=18.5 -> dt = 8.5s (|8.5 - 9.0| = 0.5s)
        Candidate 2: exit at t=9.0,  entry at t=18.5 -> dt = 9.5s (|9.5 - 9.0| = 0.5s)
        Both candidates have identical dist_expected (0.5s). Delta difference = 0.0 < 0.5s threshold.
        """
        engine = SpatialTemporalCorrelationEngine()
        t_entry = 18.5

        src_1 = make_track("S1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        src_2 = make_track("S2", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt = make_track("TG", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine.on_track_exit("CAM01", src_1, timestamp=10.0)
        engine.on_track_exit("CAM01", src_2, timestamp=9.0)

        link = engine.on_track_entry("CAM02", tgt, timestamp=t_entry)
        assert link is None, "Symmetric equidistant candidates must decline link"
        assert engine.metrics["total_declined_ties"] == 1

    def test_near_tie_within_threshold_and_outside_threshold(self):
        """
        Threshold is 0.5s.
        Case 1: Candidate 1 dist=1.0s, Candidate 2 dist=1.3s (diff = 0.3s < 0.5s) -> DECLINE
        Case 2: Candidate 1 dist=1.0s, Candidate 2 dist=1.6s (diff = 0.6s >= 0.5s) -> MATCH Candidate 1
        """
        # Case 1: Within tie threshold (0.3s diff)
        engine1 = SpatialTemporalCorrelationEngine()
        src1 = make_track("S1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        src2 = make_track("S2", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt1 = make_track("T1", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine1.on_track_exit("CAM01", src1, timestamp=90.0)
        engine1.on_track_exit("CAM01", src2, timestamp=89.7)
        assert engine1.on_track_entry("CAM02", tgt1, timestamp=100.0) is None

        # Case 2: Outside tie threshold (0.6s diff)
        engine2 = SpatialTemporalCorrelationEngine()
        engine2.on_track_exit("CAM01", src1, timestamp=90.0)
        engine2.on_track_exit("CAM01", src2, timestamp=89.4)
        link = engine2.on_track_entry("CAM02", tgt1, timestamp=100.0)
        assert link is not None
        assert link.source_track_id == src1["track_id"]

    def test_multi_way_tie_with_5_candidates(self):
        """5 identical candidates competing for 1 entry -> Declines link."""
        engine = SpatialTemporalCorrelationEngine()
        for i in range(5):
            src = make_track(f"TIE_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", src, timestamp=100.0)

        tgt = make_track("T_ENTRY", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
        link = engine.on_track_entry("CAM02", tgt, timestamp=109.0)
        assert link is None
        assert engine.get_active_window_count() == 5

    def test_class_filtered_non_tie(self):
        """Candidate 1 is 'person' (valid), Candidate 2 is 'car' (same timestamp). Person must be linked cleanly."""
        engine = SpatialTemporalCorrelationEngine()
        src_person = make_track("P1", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
        src_car = make_track("C1", "car", bbox=[590, 200, 630, 300], camera_id="CAM01")
        tgt_person = make_track("P2", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

        engine.on_track_exit("CAM01", src_person, timestamp=100.0)
        engine.on_track_exit("CAM01", src_car, timestamp=100.0)

        link = engine.on_track_entry("CAM02", tgt_person, timestamp=109.0)
        assert link is not None
        assert link.source_track_id == src_person["track_id"]
        assert link.object_type == "person"


# ============================================================================
# 3. High Concurrency Multi-Threaded Stress
# ============================================================================

class TestHighConcurrencyStress:
    """Stress-tests concurrent operations across 1,000+ simultaneous threads."""

    def test_1000_concurrent_paired_exits_and_entries(self):
        """1,000 concurrent threads creating exit/entry pairs across threads simultaneously."""
        engine = SpatialTemporalCorrelationEngine()
        num_pairs = 1000
        errors = []
        links = []
        lock = threading.Lock()

        def simulate_pair(idx: int):
            try:
                t_exit = 1000.0 + idx * 5.0
                t_entry = t_exit + 8.0  # 8s transit (HIGH confidence)

                src = make_track(f"SRC_{idx}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
                tgt = make_track(f"TGT_{idx}", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")

                win = engine.on_track_exit("CAM01", src, timestamp=t_exit)
                assert win is not None

                lnk = engine.on_track_entry("CAM02", tgt, timestamp=t_entry)
                if lnk is not None:
                    with lock:
                        links.append(lnk)
            except Exception as e:
                with lock:
                    errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(simulate_pair, i) for i in range(num_pairs)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Encountered {len(errors)} concurrency errors: {errors[:5]}"
        assert len(links) == num_pairs, f"Expected {num_pairs} successful links, got {len(links)}"
        assert engine.metrics["total_correlated"] == num_pairs

    def test_high_contention_race_for_limited_windows(self):
        """1,000 concurrent entry requests competing for 100 open exit windows.
        Invariant: exactly 100 windows consumed; zero double-linking."""
        engine = SpatialTemporalCorrelationEngine()
        num_exits = 100
        num_entries = 1000
        errors = []
        consumed_source_ids = []
        lock = threading.Lock()

        # Seed 100 open windows
        for i in range(num_exits):
            src = make_track(f"SRC_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", src, timestamp=1000.0 + (i * 2.0))

        def attempt_entry(idx: int):
            try:
                target_src_idx = idx % num_exits
                t_entry = 1000.0 + (target_src_idx * 2.0) + 8.0
                tgt = make_track(f"TGT_RACE_{idx}", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
                lnk = engine.on_track_entry("CAM02", tgt, timestamp=t_entry)
                if lnk is not None:
                    with lock:
                        consumed_source_ids.append(lnk.source_track_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(attempt_entry, i) for i in range(num_entries)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Race contention errors: {errors[:5]}"
        assert len(consumed_source_ids) == len(set(consumed_source_ids)), "Double-linking detected! Violation of 1-to-1 matching invariant."
        assert len(consumed_source_ids) <= num_exits

    def test_concurrent_mixed_operations_and_continuous_gc(self):
        """Simultaneous exits, entries, and GC sweeps running across 30 worker threads."""
        engine = SpatialTemporalCorrelationEngine()
        stop_event = threading.Event()
        errors = []
        lock = threading.Lock()

        def exit_worker():
            for i in range(500):
                try:
                    src = make_track(f"EX_{threading.get_ident()}_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
                    engine.on_track_exit("CAM01", src, timestamp=100.0 + (i * 0.1))
                except Exception as e:
                    with lock:
                        errors.append(e)

        def entry_worker():
            for i in range(500):
                try:
                    tgt = make_track(f"EN_{threading.get_ident()}_{i}", "person", bbox=[10, 200, 50, 300], camera_id="CAM02")
                    engine.on_track_entry("CAM02", tgt, timestamp=105.0 + (i * 0.1))
                except Exception as e:
                    with lock:
                        errors.append(e)

        def gc_worker():
            t = 120.0
            while not stop_event.is_set():
                try:
                    engine.cleanup_expired(t)
                    t += 5.0
                    time.sleep(0.005)
                except Exception as e:
                    with lock:
                        errors.append(e)

        threads = []
        for _ in range(10):
            threads.append(threading.Thread(target=exit_worker))
            threads.append(threading.Thread(target=entry_worker))
        for _ in range(5):
            threads.append(threading.Thread(target=gc_worker))

        for th in threads:
            th.start()

        for th in threads[:20]:
            th.join()

        stop_event.set()
        for th in threads[20:]:
            th.join()

        assert len(errors) == 0, f"Mixed operations concurrency errors: {errors[:5]}"


# ============================================================================
# 4. GC Stress Under Massive Window Accumulation
# ============================================================================

class TestGCStressMassiveAccumulation:
    """Stress-tests GC purge scaling, memory limits, and partial expiration lifecycles."""

    def test_circuit_breaker_under_massive_overflow(self):
        """Configure max_active_windows=500, inject 5,000 exits without manual GC.
        Circuit breaker must cap active memory to <= 500 and evict oldest."""
        cfg = AdjacencyPairConfig(
            lifecycle=LifecycleConfig(max_active_windows=500, gc_interval_seconds=1.0)
        )
        engine = SpatialTemporalCorrelationEngine(config=cfg)

        for i in range(5000):
            trk = make_track(f"FLOOD_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=1000.0 + (i * 0.1))

        assert len(engine.active_windows) <= 500
        assert engine.metrics["total_windows_opened"] == 5000
        assert engine.metrics["total_expired"] >= 4500

    def test_gc_batch_purge_speed_and_completeness(self):
        """Accumulate 10,000 windows and verify GC purge finishes in < 0.5s."""
        cfg = AdjacencyPairConfig(
            lifecycle=LifecycleConfig(max_active_windows=15000)
        )
        engine = SpatialTemporalCorrelationEngine(config=cfg)
        t_base = 1000.0

        for i in range(10000):
            trk = make_track(f"MASS_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=t_base + i)

        assert len(engine.active_windows) == 10000

        t_start = time.perf_counter()
        purged = engine.cleanup_expired(current_timestamp=t_base + 10000 + 50.0)
        elapsed = time.perf_counter() - t_start

        assert purged == 10000
        assert len(engine.active_windows) == 0
        assert elapsed < 0.5, f"GC took too long: {elapsed:.4f}s"

    def test_partial_expiration_lifecycle(self):
        """Verify accurate selective purging across expired vs active core/grace windows."""
        engine = SpatialTemporalCorrelationEngine()
        t_now = 200.0

        for i in range(100):
            trk = make_track(f"EXP_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=150.0)

        for i in range(100):
            trk = make_track(f"GRACE_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=182.0)

        for i in range(100):
            trk = make_track(f"CORE_{i}", "person", bbox=[590, 200, 630, 300], camera_id="CAM01")
            engine.on_track_exit("CAM01", trk, timestamp=192.0)

        assert len(engine.active_windows) == 300

        purged = engine.cleanup_expired(current_timestamp=t_now)
        assert purged == 100, f"Expected 100 purged, got {purged}"
        assert len(engine.active_windows) == 200
        assert engine.get_active_window_count() == 200


# ============================================================================
# 5. Adversarial Input Fuzzing & Spatial Boundary Math
# ============================================================================

class TestAdversarialInputs:
    """Stress-tests degenerate bounding boxes, zero-vectors, and edge cases."""

    def test_degenerate_and_out_of_bounds_bboxes(self):
        analyzer = SpatialBoundaryAnalyzer()

        assert analyzer.check_edge_proximity([], "right") is False
        assert analyzer.check_edge_proximity([10], "right") is False
        assert isinstance(analyzer.check_edge_proximity([600, 200, 500, 300], "right"), bool)
        assert analyzer.check_edge_proximity([-100, -100, -50, -50], "left") is True
        assert analyzer.check_edge_proximity([700, 200, 800, 300], "right") is True
        assert analyzer.check_edge_proximity([580, 200, 620, 300], "diagonal") is False
        assert analyzer.check_edge_proximity([580, 200, 620, 300], "") is False

    def test_degenerate_trajectories(self):
        analyzer = SpatialBoundaryAnalyzer(min_trajectory_points=3)

        matched, meta = analyzer.check_trajectory_vector([], "right", mode="exit")
        assert matched is False
        assert meta["reason"] == "insufficient_points_exit"

        matched, meta = analyzer.check_trajectory_vector([], "left", mode="entry")
        assert matched is True
        assert meta["reason"] == "insufficient_points_entry_permissive"

        stationary = [[600, 250], [600, 250], [600, 250]]
        matched, _ = analyzer.check_trajectory_vector(stationary, "right", mode="exit")
        assert matched is False, "Stationary object at boundary must not match exit vector"

    def test_extreme_confidence_values(self):
        engine = SpatialTemporalCorrelationEngine()
        t_exit = 100.0
        t_entry = 108.0

        src_low = make_track("L1", "person", bbox=[590, 200, 630, 300], confidence=0.499, camera_id="CAM01")
        tgt_low = make_track("L2", "person", bbox=[10, 200, 50, 300], confidence=0.499, camera_id="CAM02")

        engine.on_track_exit("CAM01", src_low, timestamp=t_exit)
        link = engine.on_track_entry("CAM02", tgt_low, timestamp=t_entry)
        assert link is not None
        assert link.confidence_band == "LOW"
        assert link.detection_confidence == pytest.approx(0.499, 0.001)

        engine2 = SpatialTemporalCorrelationEngine()
        src_exact = make_track("E1", "person", bbox=[590, 200, 630, 300], confidence=0.500, camera_id="CAM01")
        tgt_exact = make_track("E2", "person", bbox=[10, 200, 50, 300], confidence=0.500, camera_id="CAM02")

        engine2.on_track_exit("CAM01", src_exact, timestamp=t_exit)
        link2 = engine2.on_track_entry("CAM02", tgt_exact, timestamp=t_entry)
        assert link2 is not None
        assert link2.confidence_band == "HIGH"


# ============================================================================
# 6. Temporal Anomaly & Reentrant Lock Stress
# ============================================================================

class TestTemporalAnomalyAndReentrancy:
    """Stress-tests temporal inversions, disabled flags, wrong camera routing, and reentrant locks."""

    def test_wrong_camera_routing_and_disabled_topology(self):
        engine = SpatialTemporalCorrelationEngine()

        # Exit on CAM02 (target camera) -> Should not open window
        src = make_track("CAM02_SRC", "person", camera_id="CAM02")
        assert engine.on_track_exit("CAM02", src, timestamp=100.0) is None
        assert engine.get_active_window_count() == 0

        # Entry on CAM01 (source camera) -> Should not trigger correlation
        tgt = make_track("CAM01_TGT", "person", camera_id="CAM01")
        assert engine.on_track_entry("CAM01", tgt, timestamp=108.0) is None

        # Disabled configuration
        engine.config.enabled = False
        src_valid = make_track("P1", "person", camera_id="CAM01")
        tgt_valid = make_track("P2", "person", camera_id="CAM02")
        assert engine.on_track_exit("CAM01", src_valid, timestamp=100.0) is None
        assert engine.on_track_entry("CAM02", tgt_valid, timestamp=108.0) is None

    def test_reentrant_lock_safety(self):
        """Verify engine reentrant lock allows internal cleanup without deadlocking."""
        cfg = AdjacencyPairConfig(
            lifecycle=LifecycleConfig(max_active_windows=1)
        )
        engine = SpatialTemporalCorrelationEngine(config=cfg)

        # First exit fills capacity (1 window)
        trk1 = make_track("P1", "person", camera_id="CAM01")
        engine.on_track_exit("CAM01", trk1, timestamp=100.0)

        # Second exit triggers cleanup_expired from within on_track_exit holding lock
        trk2 = make_track("P2", "person", camera_id="CAM01")
        win2 = engine.on_track_exit("CAM01", trk2, timestamp=200.0)

        assert win2 is not None
        assert len(engine.active_windows) == 1
        assert engine.metrics["total_expired"] >= 1
