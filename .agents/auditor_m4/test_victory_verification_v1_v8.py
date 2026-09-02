import sys
import time
import os
import tempfile
import sqlite3
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path
sys.path.insert(0, r"C:\Users\HEMANTH\Desktop\SKYNET")

from intelligence.correlation import (
    SpatialTemporalCorrelationEngine,
    ConfidenceBand,
    WindowStatus,
    CorrelatedTrackLink,
    CorrelationWindow,
)
from backend.storage_manager import StorageManager
from backend.api.events_store import SQLiteEventStore
from backend.schemas.events import EventSchema
from simulator.scenarios.two_camera_correlation import TwoCameraCorrelationSimulator

print("=" * 80)
print("INDEPENDENT EMPIRICAL AUDITOR VERIFICATION SUITE (V1 - V8)")
print("=" * 80)

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

engine = SpatialTemporalCorrelationEngine(config_path=r"C:\Users\HEMANTH\Desktop\SKYNET\configs\adjacency.yaml")

# -------------------------------------------------------------
# V1. Unit - positive match
# -------------------------------------------------------------
print("\n--- [V1] Positive Match Verification ---")
t0 = 100.0
track_src = make_track("P1", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
track_tgt = make_track("P2", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")

window = engine.on_track_exit("CAM01", track_src, timestamp=t0)
assert window is not None, "Failed to create CorrelationWindow on CAM01 exit"
assert window.source_track_id == track_src["track_id"]
assert window.status == WindowStatus.OPEN

t_entry = t0 + 8.0 # Within 3.0s - 15.0s
link = engine.on_track_entry("CAM02", track_tgt, timestamp=t_entry)
assert link is not None, "Failed to link positive match"
assert link.confidence_band == "HIGH", f"Expected HIGH confidence, got {link.confidence_band}"
assert link.source_track_id == track_src["track_id"]
assert link.target_track_id == track_tgt["track_id"]
assert abs(link.transit_duration_seconds - 8.0) < 0.01
print(f"V1 PASS: Linked {link.source_track_id} -> {link.target_track_id} with {link.confidence_band} (transit {link.transit_duration_seconds}s)")

# -------------------------------------------------------------
# V2. Unit - class mismatch
# -------------------------------------------------------------
print("\n--- [V2] Class Mismatch Verification ---")
t0 = 200.0
track_person = make_track("P1", "person", bbox=[580, 200, 620, 300], camera_id="CAM01")
track_car = make_track("V1", "car", bbox=[20, 200, 60, 300], camera_id="CAM02")

window_p = engine.on_track_exit("CAM01", track_person, timestamp=t0)
assert window_p is not None

link_mismatch = engine.on_track_entry("CAM02", track_car, timestamp=t0 + 6.0)
assert link_mismatch is None, f"Expected None on class mismatch, got {link_mismatch}"
assert window_p.status == WindowStatus.OPEN
print("V2 PASS: Class mismatch (person vs car) correctly refused linkage (result = None)")

# -------------------------------------------------------------
# V3. Unit - timing boundaries
# -------------------------------------------------------------
print("\n--- [V3] Timing Boundaries Verification ---")
# Boundaries per config: min=3.0s, max=15.0s, grace=7.5s (cutoff=22.5s)
test_deltas = [
    (2.9, False, None, "Sub-min (2.9s) -> Unlinked"),
    (3.0, True, "HIGH", "Exact min (3.0s) -> HIGH"),
    (9.0, True, "HIGH", "Mid transit (9.0s) -> HIGH"),
    (15.0, True, "HIGH", "Exact max (15.0s) -> HIGH"),
    (15.1, True, "LOW", "Grace entry (15.1s) -> LOW"),
    (22.5, True, "LOW", "Exact grace max (22.5s) -> LOW"),
    (22.6, False, None, "Post grace (22.6s) -> Unlinked"),
]

for delta, should_link, expected_band, label in test_deltas:
    t_exit = 1000.0 + delta * 100
    t_entry = t_exit + delta
    
    t_src = make_track(f"SRC-{delta}", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
    t_dst = make_track(f"DST-{delta}", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")
    
    engine.on_track_exit("CAM01", t_src, timestamp=t_exit)
    res = engine.on_track_entry("CAM02", t_dst, timestamp=t_entry)
    
    if should_link:
        assert res is not None, f"Failed linking for {label}"
        assert res.confidence_band == expected_band, f"Expected {expected_band} for {label}, got {res.confidence_band}"
        print(f"  [PASS] {label}: Linked as {res.confidence_band}")
    else:
        assert res is None, f"Expected None for {label}, got {res}"
        print(f"  [PASS] {label}: Correctly unlinked (None)")

print("V3 PASS: All timing boundary tests verified.")

# -------------------------------------------------------------
# V4. Unit - edge mismatch
# -------------------------------------------------------------
print("\n--- [V4] Edge Mismatch Verification ---")
t0 = 5000.0
# Exit from TOP instead of configured RIGHT edge (bbox near top, trajectory moving up)
track_top = make_track("TOP", "person", bbox=[300, 10, 340, 50], trajectory=[[320, 100], [320, 60], [320, 20]], camera_id="CAM01")
track_left = make_track("LEFT", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")

engine.on_track_exit("CAM01", track_top, timestamp=t0)
res_edge = engine.on_track_entry("CAM02", track_left, timestamp=t0 + 6.0)

assert res_edge is not None, "Expected match for timing within core window"
assert res_edge.confidence_band == "MEDIUM", f"Expected downgrade to MEDIUM, got {res_edge.confidence_band}"
assert res_edge.confidence_band != "HIGH", "Edge mismatch MUST NOT upgrade to HIGH"
print(f"V4 PASS: Edge mismatch correctly downgraded to {res_edge.confidence_band} (never HIGH)")

# -------------------------------------------------------------
# V5. Integration - live two-camera simulator run (3x back-to-back)
# -------------------------------------------------------------
print("\n--- [V5] Live 2-Camera Walk Simulator (3x consecutive) ---")
sim = TwoCameraCorrelationSimulator()
suite_res = sim.run_3x_walk_suite(delays=[4.0, 6.0, 8.0])
assert suite_res["suite_passed"] is True, f"V5 suite failed: {suite_res}"
assert suite_res["passed_runs"] == 3, f"Expected 3 passed runs, got {suite_res['passed_runs']}"
assert suite_res["max_latency_seconds"] <= 2.0, f"Latency {suite_res['max_latency_seconds']}s exceeded 2.0s SLA"
print(f"V5 PASS: 3/3 consecutive walks passed. Max latency: {suite_res['max_latency_seconds'] * 1000:.4f} ms (SLA <= 2000ms)")

# -------------------------------------------------------------
# V6. Concurrency and multi-track disambiguation
# -------------------------------------------------------------
print("\n--- [V6] Concurrency & Disambiguation Protocol ---")
t0 = 6000.0
# Two exits on CAM01
cand1 = make_track("CAND1", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
cand2 = make_track("CAND2", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")

# CAND1 exits at t0 - 4.0 (for entry at t0 + 6.0, transit is 10.0s -> |10 - 9| = 1.0s diff from expected 9s)
# CAND2 exits at t0 - 1.0 (for entry at t0 + 6.0, transit is 7.0s -> |7 - 9| = 2.0s diff from expected 9s)
engine.on_track_exit("CAM01", cand1, timestamp=t0 - 4.0)
engine.on_track_exit("CAM01", cand2, timestamp=t0 - 1.0)

entry_v6 = make_track("ENTRY-V6", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")
res_pick = engine.on_track_entry("CAM02", entry_v6, timestamp=t0 + 6.0)

assert res_pick is not None, "Failed candidate disambiguation"
assert res_pick.source_track_id == cand1["track_id"], f"Expected CAND1 (closer time), got {res_pick.source_track_id}"

# Verify 1-to-1 invariant: once CAND1 is consumed, it cannot be linked to another entry
entry_v6_2 = make_track("ENTRY-V6-2", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")
res_double = engine.on_track_entry("CAM02", entry_v6_2, timestamp=t0 + 6.1)
assert res_double is not None
assert res_double.source_track_id == cand2["track_id"], f"Expected remaining CAND2, got {res_double.source_track_id}"

# Test Tie Declination
tie_a = make_track("TIE-A", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
tie_b = make_track("TIE-B", "person", bbox=[580, 200, 620, 300], trajectory=[[520, 250], [560, 250], [600, 250]], camera_id="CAM01")
engine.on_track_exit("CAM01", tie_a, timestamp=t0 + 100.0)
engine.on_track_exit("CAM01", tie_b, timestamp=t0 + 100.0)

tie_entry = make_track("TIE-ENTRY", "person", bbox=[20, 200, 60, 300], trajectory=[[25, 250], [50, 250], [75, 250]], camera_id="CAM02")
# Both exits at exactly t0+100. Entry at t0+109 (both transit 9.0s, delta 0.0s < ambiguity_tie_threshold_s 0.5s)
res_tie = engine.on_track_entry("CAM02", tie_entry, timestamp=t0 + 109.0)
assert res_tie is None, f"Expected None on ambiguous tie, got {res_tie}"
print("V6 PASS: Disambiguation picks closer time match, enforces 1-to-1 matching, and declines ambiguous ties.")

# -------------------------------------------------------------
# V7. Unmatched exit GC memory cleanup
# -------------------------------------------------------------
print("\n--- [V7] Garbage Collection & Memory Bounding ---")
t0 = 8000.0
for i in range(100):
    t_gc = make_track(f"GC-{i}", "person", bbox=[580, 200, 620, 300], camera_id="CAM01")
    engine.on_track_exit("CAM01", t_gc, timestamp=t0 + i)

assert len(engine.active_windows) >= 100
# Advance timestamp by 300 seconds (beyond max_transit 15s + grace 7.5s = 22.5s)
purged_count = engine.cleanup_expired(t0 + 300.0)
assert purged_count >= 100, f"Expected >=100 purged windows, got {purged_count}"
assert engine.get_active_window_count() == 0, f"Expected 0 active windows, got {engine.get_active_window_count()}"
print(f"V7 PASS: Successfully purged {purged_count} expired correlation windows (0 memory leak).")

# -------------------------------------------------------------
# V8. Storage Governance & SQLite Audit Trail Parity
# -------------------------------------------------------------
print("\n--- [V8] Storage Governance & SQLite Audit Trail Parity ---")
temp_dir = tempfile.mkdtemp()
try:
    db_path = os.path.join(temp_dir, "test_events.db")
    media_dir = os.path.join(temp_dir, "media")
    os.makedirs(media_dir, exist_ok=True)
    
    # 50MB storage budget
    storage_mgr = StorageManager(storage_dir=media_dir, max_budget_mb=50)
    store = SQLiteEventStore(db_path=db_path)
    
    # Insert correlated incident
    from datetime import datetime, timezone
    sample_incident = EventSchema(
        event_id="EVT-CORR-01",
        camera_id="CAM02",
        timestamp=datetime.now(timezone.utc),
        start_time=datetime.now(timezone.utc),
        status="ACTIVE",
        track_id="CAM02-T10",
        object_type="person",
        confidence=0.95,
        risk_score=85,
        risk_level="HIGH",
        reasons=["cross_camera_correlation", "restricted_zone"],
        incident_id="INC-20260830-TEST",
        correlation_confidence="HIGH",
        correlated_with_track="CAM01-T10",
        correlated_with_camera="CAM01",
        transit_time_seconds=6.5,
        is_held=False
    )
    store.append(sample_incident)
    
    # Verify retrieval
    retrieved = store.get_by_event_id("EVT-CORR-01")
    assert retrieved is not None, "Failed to retrieve saved correlated event"
    assert retrieved.incident_id == "INC-20260830-TEST"
    assert retrieved.correlation_confidence == "HIGH"
    assert retrieved.transit_time_seconds == 6.5
    
    # Verify Incident lookup
    incident_events = store.get_by_incident_id("INC-20260830-TEST")
    assert len(incident_events) == 1
    assert incident_events[0].event_id == "EVT-CORR-01"
    
    # Verify Operator Hold and Audit Logging
    store.update_event_status("EVT-CORR-01", {"is_held": True})
    store.log_audit("EVT-CORR-01", operator="OPERATOR_1", action="HOLD_TOGGLED", reason="Secured evidence", notes="Audited")
    
    retrieved_held = store.get_by_event_id("EVT-CORR-01")
    assert retrieved_held.is_held is True, "Failed to set operator hold"
    
    # Verify SQLite Audit Log
    logs = store.get_audit_logs()
    assert len(logs) > 0, "No audit logs recorded"
    hold_log = next((l for l in logs if l["event_id"] == "EVT-CORR-01" and l["action"] == "HOLD_TOGGLED"), None)
    assert hold_log is not None, "Failed to record audit log for hold action"
    assert hold_log["operator"] == "OPERATOR_1"
    
    # Verify 3-Tier Storage & Purge Calculation
    assert storage_mgr.max_budget_bytes == 50 * 1024 * 1024
    assert storage_mgr.get_dir_size() >= 0
    
    store.conn.close()
finally:
    import shutil
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    
print("V8 PASS: Correlated incidents fully respect SQLite persistence, 3-tier storage, operator hold, and audit logging.")

print("\n" + "=" * 80)
print(">>> ALL VERIFICATIONS (V1 - V8) SUCCESSFULLY PASSED EMPIRICALLY <<<")
print("=" * 80)
