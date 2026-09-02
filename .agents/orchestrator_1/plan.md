# Project Plan: SKYNET Cross-Camera Spatial-Temporal Correlation Engine

## Objective
Implement a cross-camera spatial-temporal correlation engine linking tracks across exactly 2 cameras using adjacency maps, transit windows, and object class matching without appearance-based Re-ID embeddings, meeting R1-R3, V1-V8, and all acceptance criteria.

## Phases

### Phase 0: Survey & Codebase Reconnaissance
- Dispatch 3 Explorers / Spec Miners:
  - Explorer 1 (Spec Miner): Detailed mapping of requirements R1-R3, V1-V8, acceptance criteria, edge cases, confidence band rules.
  - Explorer 2 (Codebase & Architecture): Investigate existing modules (`backend`, `camera`, `ai`, `intelligence`, `simulator`, `dashboard`, `storage`), track data models, event ingestion pipeline, incident schema.
  - Explorer 3 (Test Suite & Verification Harness): Investigate existing tests (`tests/`), test infrastructure, execution environment, how V1-V8 can be tested and verified.
- Synthesize into `PROJECT.md` with full Feature Inventory, Architecture, Milestones, and Interface Contracts.

### Phase 1: Dual Track Launch
- **Track A: E2E Testing Track**
  - E2E Test infrastructure & test suites (Tiers 1-4) covering all V1-V8 and acceptance criteria.
  - Produce `TEST_READY.md`.
- **Track B: Implementation Track**
  - Milestone 1: Adjacency configuration schema, models, and spatial exit/entry edge calculation & transit window engine.
  - Milestone 2: Correlation engine, confidence banding (HIGH, MEDIUM, LOW, None), concurrency handling, and incident linkage.
  - Milestone 3: Simulator integration, live pipeline hookup, cleanup of unmatched windows, storage governance & audit trail integration.
  - Milestone 4: Dashboard UI updates (visible confidence band on event card and incident detail, no "same person" claims, live 2-camera correlation demo).

### Phase 2: Final Verification & Adversarial Hardening
- Run full test suite & V1-V8 verification.
- Phase 1: 100% E2E test pass (Tiers 1-4).
- Phase 2: Adversarial coverage hardening (Tier 5) with Challenger.
- Forensic Auditor integrity review.
- Victory validation & final report to Sentinel.
