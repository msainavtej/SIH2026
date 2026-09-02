import sys
import os
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pytest

print("=" * 80)
print("INDEPENDENT VICTORY AUDIT TEST EXECUTION SUITE")
print("Python Environment:", sys.version)
print("=" * 80)

# Run full pytest suite
print("\n--- 1. PYTEST TEST SUITE (tests/) ---")
retcode = pytest.main(["-v", "--import-mode=importlib", "tests/"])
print(f"\nPytest exit code: {retcode}")

# Run simulator scenarios
print("\n--- 2. BASELINE SCENARIOS (simulator.scenarios.test_scenarios) ---")
try:
    from simulator.scenarios.test_scenarios import run_all_scenarios, run_camera_tests
    core_passed, core_total = run_all_scenarios()
    cam_passed, cam_total = run_camera_tests()
    print(f"Core scenarios: {core_passed}/{core_total} passed.")
    print(f"Camera scenarios: {cam_passed}/{cam_total} passed.")
    print(f"Total baseline scenarios: {core_passed + cam_passed}/{core_total + cam_total} passed.")
except Exception as e:
    print(f"Baseline scenarios execution failed: {e}")

# Run live 2-camera correlation scenario
print("\n--- 3. LIVE 2-CAMERA SIMULATION 3X (simulator.scenarios.two_camera_correlation) ---")
try:
    from simulator.scenarios.two_camera_correlation import run_live_scenario
    live_success = run_live_scenario(real_time=False)
    print(f"Live 2-Camera Simulation Result: {'SUCCESS' if live_success else 'FAILED'}")
except Exception as e:
    print(f"Live 2-Camera Simulation failed: {e}")

print("\n" + "=" * 80)
print("TEST EXECUTION COMPLETED")
print("=" * 80)
