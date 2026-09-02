## 2026-08-30T15:07:46Z
You are worker_m2, a teamwork_preview_worker subagent.

Your working directory is: C:\Users\HEMANTH\Desktop\SKYNET\.agents\worker_m2
Project root: C:\Users\HEMANTH\Desktop\SKYNET
Original user request: C:\Users\HEMANTH\Desktop\SKYNET\.agents\ORIGINAL_REQUEST.md
Project plan: C:\Users\HEMANTH\Desktop\SKYNET\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & EXCLUSIVE WRITE OWNERSHIP FOR M2:
- `backend/schemas/events.py`
- `backend/camera_manager.py`
- `intelligence/event_engine.py`
- `backend/api/events_store.py`
- `backend/storage_manager.py`

TASK INSTRUCTIONS:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and examine M1 implementations in configs/adjacency.yaml, intelligence/boundary.py, and intelligence/correlation.py.
2. Update `backend/schemas/events.py`:
   - Add correlation fields to `EventSchema`: `incident_id: Optional[str] = None`, `correlation_confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None`, `correlated_with_track: Optional[str] = None`, `correlated_with_camera: Optional[str] = None`, `transit_time_seconds: Optional[float] = None`.
3. Update `backend/camera_manager.py`:
   - Initialize a shared `SpatialTemporalCorrelationEngine` instance loaded from `configs/adjacency.yaml`.
   - In `_run_pipeline(cid)`: when tracks are processed, route new track entries to `correlation_engine.on_track_entry(cid, track)` and track exits to `correlation_engine.on_track_exit(cid, track)`.
   - When a correlation occurs (returning `CorrelatedTrackLink`), enrich the corresponding `EventSchema` instance with `incident_id`, `correlation_confidence`, `correlated_with_track`, `correlated_with_camera`, `transit_time_seconds`, and append or update `events_db`.
4. Update `intelligence/event_engine.py`:
   - Hook track resolution / loss to ensure track exit events trigger spatial-temporal correlation window creation cleanly.
5. Verify `backend/api/events_store.py` and `backend/storage_manager.py`:
   - Ensure correlated events are persisted in SQLite, indexed by event_id / incident_id, and respect 3-tier retention (Routine/Confirmed/Held), 50MB budget auto-purge, and audit logs without regression (Rule V8).
6. Run all test suites:
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/ -v
   $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"; & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m simulator.scenarios.test_scenarios
7. Ensure 100% of tests pass with 0 regressions.
8. Write progress.md and your completion report to C:\Users\HEMANTH\Desktop\SKYNET\.agents\worker_m2\handoff.md and notify the parent orchestrator via send_message.
