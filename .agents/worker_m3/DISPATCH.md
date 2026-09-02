## 2026-08-30T15:21:25Z
You are worker_m3, a teamwork_preview_worker subagent.

Your working directory is: C:\Users\HEMANTH\Desktop\SKYNET\.agents\worker_m3
Project root: C:\Users\HEMANTH\Desktop\SKYNET
Original user request: C:\Users\HEMANTH\Desktop\SKYNET\.agents\ORIGINAL_REQUEST.md
Project plan: C:\Users\HEMANTH\Desktop\SKYNET\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. An auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SCOPE & EXCLUSIVE WRITE OWNERSHIP FOR M3:
- `simulator/scenarios/two_camera_correlation.py` (or `simulator/scenarios/test_scenarios.py` multi-camera scenario runner)
- `dashboard/src/App.jsx` (and any related dashboard components)
- `tests/integration/test_two_camera_correlation.py` (if needed for simulator scenario hookup)

TASK INSTRUCTIONS:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and inspect M1 and M2 implementations.
2. Implement the live 2-camera simulator integration scenario in `simulator/scenarios/two_camera_correlation.py` (or in `simulator/`):
   - Simulates CAM01 right edge exit -> CAM02 left edge entry within transit window (3-15s).
   - Generates synthetic object trajectories moving across the configured boundary.
   - Executes 3 consecutive back-to-back walks, verifying reproducible incident creation with HIGH confidence and latency <= 2.0s from detection to incident emission (Rule V5).
3. Update `dashboard/src/App.jsx`:
   - Display categorical confidence badge (`HIGH`, `MEDIUM`, `LOW`) prominently on the Active Events card and in the Incident Detail modal (never hidden behind a tooltip).
   - Ensure the UI text strictly complies with anti-overclaim rules: e.g. "Correlated Track Link [HIGH]" or "Track #<id> correlated across CAM01 -> CAM02", NEVER stating or implying "confirmed person" or "same person".
4. Run all integration and simulator test suites:
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/integration/test_two_camera_correlation.py -v
   & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m pytest --import-mode=importlib tests/ -v
   $env:PYTHONPATH="C:\Users\HEMANTH\Desktop\SKYNET"; & "C:\Users\HEMANTH\Desktop\SKYNET\.venv\Scripts\python.exe" -m simulator.scenarios.test_scenarios
5. Ensure all tests pass 100% with exit code 0.
6. Write progress.md and your completion report to C:\Users\HEMANTH\Desktop\SKYNET\.agents\worker_m3\handoff.md.
7. Notify the parent orchestrator via send_message when complete.
