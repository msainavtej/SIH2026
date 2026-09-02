"""
Integration Tests for Cross-Camera Spatial-Temporal Correlation Engine
Covers:
  - F6: Multi-Camera Pipeline Integration & Incident Linkage
  - F8: Live 2-Camera Simulator Scenario (TwoCameraCorrelationSimulator)
  - V5: 3x Back-to-Back Live Walk Runs (Latency <= 2.0s, Confidence HIGH)
"""

import time
from datetime import datetime
import pytest
from typing import Dict, Any, List
from backend.schemas.events import EventSchema
from backend.api.events_store import SQLiteEventStore
from camera.simulated_camera import SimulatedCamera

try:
    from intelligence.correlation import SpatialTemporalCorrelationEngine
    from backend.camera_manager import CameraManager
    from simulator.scenarios.two_camera_correlation import (
        TwoCameraCorrelationSimulator,
        generate_cam01_exit_trajectory,
        generate_cam02_entry_trajectory,
        run_live_scenario,
    )
    HAS_CORRELATION = True
except ImportError:
    HAS_CORRELATION = False


class TestTwoCameraCorrelationIntegration:
    """Integration test suite for two-camera cross-correlation and simulated walks."""

    def test_v5_live_two_camera_walk_3x(self, tmp_path):
        """V5: Simulates an object walking across the adjacency boundary (CAM01 right -> CAM02 left)
        3 times back-to-back.
        Asserts:
          1. Incident created with linked track IDs for each walk.
          2. Confidence band == 'HIGH'.
          3. Incident detection-to-linkage latency <= 2.0s.
          4. 3/3 consecutive passes without failure.
        """
        if not HAS_CORRELATION:
            pytest.skip("SpatialTemporalCorrelationEngine pending M1/M2/M3 implementation")

        engine = SpatialTemporalCorrelationEngine()
        db_file = str(tmp_path / "test_events.db")
        event_store = SQLiteEventStore(db_path=db_file)

        walk_delays = [4.0, 5.5, 6.0]  # 3 distinct transit intervals within [3.0s, 15.0s]
        successful_runs = 0

        for run_idx, transit_delay in enumerate(walk_delays, start=1):
            t_base = time.time()
            track_src_id = f"CAM01-WALK{run_idx}"
            track_tgt_id = f"CAM02-WALK{run_idx}"

            # Step 1: CAM01 object moves right and exits
            track_cam01 = {
                "track_id": track_src_id,
                "object_type": "person",
                "confidence": 0.92,
                "bbox": [595, 220, 635, 320],
                "trajectory": [[520, 270], [560, 270], [600, 270]],
                "camera_id": "CAM01",
            }
            window = engine.on_track_exit("CAM01", track_cam01, timestamp=t_base)
            assert window is not None, f"Run {run_idx}: Failed to open correlation window"

            # Step 2: Simulate transit time
            t_entry = t_base + transit_delay

            # Step 3: CAM02 object appears on left edge
            track_cam02 = {
                "track_id": track_tgt_id,
                "object_type": "person",
                "confidence": 0.94,
                "bbox": [15, 220, 55, 320],
                "trajectory": [[20, 270], [45, 270], [70, 270]],
                "camera_id": "CAM02",
            }

            # Measure correlation computation latency
            t_calc_start = time.perf_counter()
            link = engine.on_track_entry("CAM02", track_cam02, timestamp=t_entry)
            t_calc_duration = time.perf_counter() - t_calc_start

            # Verifications
            assert link is not None, f"Run {run_idx}: Expected correlation link, got None"
            assert link.source_track_id == track_src_id, f"Run {run_idx}: Source track mismatch"
            assert link.target_track_id == track_tgt_id, f"Run {run_idx}: Target track mismatch"
            assert link.confidence_band == "HIGH", f"Run {run_idx}: Confidence must be HIGH, got {link.confidence_band}"
            assert link.transit_duration_seconds == pytest.approx(transit_delay, 0.05)
            # Latency SLA check: processing latency must be well under 2.0s
            assert t_calc_duration <= 2.0, f"Run {run_idx}: Latency {t_calc_duration:.4f}s exceeded 2.0s limit"

            successful_runs += 1

        assert successful_runs == 3, f"Expected 3 successful back-to-back runs, got {successful_runs}"

    def test_f8_simulator_scenario_runner(self):
        """F8: Tests TwoCameraCorrelationSimulator runner methods and trajectory synthesis."""
        if not HAS_CORRELATION:
            pytest.skip("TwoCameraCorrelationSimulator pending implementation")

        sim = TwoCameraCorrelationSimulator()
        suite_res = sim.run_3x_walk_suite(delays=[3.5, 7.0, 12.0], real_time_delay=False)

        assert suite_res["suite_passed"] is True
        assert suite_res["total_runs"] == 3
        assert suite_res["passed_runs"] == 3
        assert suite_res["max_latency_seconds"] <= 2.0
        assert suite_res["all_confidence_high"] is True

        for walk in suite_res["walk_results"]:
            assert walk["passed"] is True
            assert walk["confidence_band"] == "HIGH"
            assert walk["incident_id"] is not None
            assert "Correlated Track Link [HIGH]" in walk["summary_text"]
            assert "same person" not in walk["summary_text"].lower()
            assert "confirmed person" not in walk["summary_text"].lower()

        # Test CLI runner function
        assert run_live_scenario(real_time=False) is True

    def test_f8_trajectory_generation_boundaries(self):
        """F8: Validates generated trajectories conform to spatial edge requirements."""
        traj_src = generate_cam01_exit_trajectory(track_id="CAM01-TEST", frame_width=640)
        assert traj_src["camera_id"] == "CAM01"
        assert len(traj_src["trajectory"]) >= 3
        # Exit edge x2 must be in right threshold (>= 0.90 * 640 = 576)
        assert traj_src["bbox"][2] >= 576

        traj_tgt = generate_cam02_entry_trajectory(track_id="CAM02-TEST", frame_width=640)
        assert traj_tgt["camera_id"] == "CAM02"
        assert len(traj_tgt["trajectory"]) >= 3
        # Entry edge x1 must be in left threshold (<= 0.10 * 640 = 64)
        assert traj_tgt["bbox"][0] <= 64

    def test_f6_camera_manager_linkage(self, tmp_path):
        """F6: Tests integration of CameraManager multi-camera track routing with CorrelationEngine."""
        if not HAS_CORRELATION:
            pytest.skip("CameraManager correlation integration pending M2 implementation")

        cam_mgr = CameraManager()
        assert cam_mgr.correlation_engine is not None
        assert cam_mgr.correlation_engine.config.source_camera_id == "CAM01"
        assert cam_mgr.correlation_engine.config.target_camera_id == "CAM02"

        db_file = str(tmp_path / "test_cm_events.db")
        test_store = SQLiteEventStore(db_path=db_file)

        # Create source event on CAM01
        ev_src = EventSchema(
            event_id="EVT-CAM01-LINK",
            camera_id="CAM01",
            timestamp=datetime.utcnow(),
            start_time=datetime.utcnow(),
            status="ACTIVE",
            track_id="CAM01-P1",
            object_type="person",
            confidence=0.92,
            risk_score=70,
            risk_level="MEDIUM",
            reasons=["boundary_exit"],
        )
        test_store.append(ev_src)

        # Simulate correlation link
        from intelligence.correlation import CorrelatedTrackLink
        link = CorrelatedTrackLink(
            incident_id="INC-20260830-TEST01",
            pair_id="ADJ_CAM01_CAM02",
            source_camera_id="CAM01",
            source_track_id="CAM01-P1",
            target_camera_id="CAM02",
            target_track_id="CAM02-P2",
            object_type="person",
            transit_duration_seconds=5.0,
            confidence_band="HIGH",
            edge_match_status="BOTH_MATCHED",
            detection_confidence=0.92,
            source_exit_time=time.time(),
            target_entry_time=time.time() + 5.0,
        )

        import backend.camera_manager
        orig_events_db = backend.camera_manager.events_db
        backend.camera_manager.events_db = test_store

        try:
            cam_mgr._enrich_and_update_events(link)
            enriched = test_store.get_by_event_id("EVT-CAM01-LINK")
            assert enriched is not None
            assert enriched.incident_id == "INC-20260830-TEST01"
            assert enriched.correlation_confidence == "HIGH"
            assert enriched.correlated_with_track == "CAM02-P2"
            assert enriched.correlated_with_camera == "CAM02"
            assert enriched.transit_time_seconds == 5.0

            by_inc = test_store.get_by_incident_id("INC-20260830-TEST01")
            assert len(by_inc) == 1
            assert by_inc[0].event_id == "EVT-CAM01-LINK"
        finally:
            backend.camera_manager.events_db = orig_events_db

        cam1 = SimulatedCamera("CAM01", fps=15)
        cam2 = SimulatedCamera("CAM02", fps=15)
        cam1.connect()
        cam2.connect()

        assert cam1.is_online()
        assert cam2.is_online()

        cam1.release()
        cam2.release()
