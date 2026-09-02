# Original User Request

## Initial Request — 2026-08-30T14:26:16Z

# Teamwork Project Prompt - Draft

> Status: Ready for launch - awaiting user approval.
> Goal: Craft prompt   get user approval   delegate to teamwork_preview
> Requested team: [none - teamwork routes from the description]

Implement a cross-camera spatial-temporal correlation engine that links tracks across exactly 2 cameras using adjacency maps, transit windows, and object class matching, without relying on appearance-based Re-ID embeddings.

Working directory: C:\Users\HEMANTH\Desktop\SKYNET
Integrity mode: development

## Requirements

### R1. Adjacency Mapping and Transit Logic
Configure exactly one adjacency relationship between two cameras (e.g., CAM-01 right edge -> CAM-02 left edge, 3-15s transit time). When a track exits the configured edge of Camera 1, open a correlation window. If a compatible detection (matching object class) enters the linked edge of Camera 2 within the time window, link both track IDs under a single unified Incident. 
This adjacency map (edges, transit window, and confidence thresholds) must be externally configurable, not hardcoded.

### R2. Confidence Banding
Output a confidence score for the correlation as a categorical band rather than a raw percentage or a confirmed identity match. Overclaiming Re-ID accuracy is strictly forbidden.
- **HIGH:** class match + correct configured edge + timing within the core transit window (e.g., 3-15s).
- **MEDIUM:** class match + timing within the core window, but edge vector missing or ambiguous.
- **LOW:** class match + timing within a wider grace window only (e.g., up to +50% beyond the upper bound), OR edge+timing match with a borderline/low-confidence class detection.
- **Below LOW threshold:** NO correlation is created. Two unlinked, independent events is the safe default - a missed correlation is always preferable to a false one.

### R3. No Appearance-based Re-ID
Do not implement N-camera graph logic or visual embedding vectors (e.g., BoT-SORT feature extraction). Stick strictly to bounding box spatial vectors and time-series rules.

## Verification

**V1. Unit - positive match:** synthetic fixtures where a track exits CAM-01's configured edge and a same-class detection enters CAM-02's linked edge within the transit window   assert an Incident is created linking both track_ids, confidence == HIGH.

**V2. Unit - class mismatch:** person exits CAM-01, vehicle enters CAM-02 within the window   assert NOT linked.

**V3. Unit - timing boundaries:** entry at window_min - 0.1s and window_max + 0.1s   not linked (or LOW); entry at window_min and window_max inclusive   linked.

**V4. Unit - edge mismatch:** track exits through a non-configured edge (e.g. top instead of the mapped right edge)   confidence downgrades per the band rules, never silently upgrades to HIGH.

**V5. Integration - live two-camera simulator run:** manually walk one simulated object across the adjacency boundary; dashboard must show "Track #<id> confirmed on <camera>" with a visible confidence label within ~2 seconds of the entry detection. Must be reproducible on demand, not a one-time fluke - run it 3 times back to back.

**V6. Concurrency:** two candidate tracks near the exit at the same time: system must not crash and must not double-link one exit to two entries; either picks the closer time match or declines to link rather than guessing.

**V7. Cleanup:** an open correlation window with no matching entry within the transit window (+ grace period) must be discarded; confirm no unbounded memory growth from unmatched exits over an extended run.

**V8. Regression:** full existing test suite (single-camera pipeline, storage governance, audit trail) still passes unmodified.

## Acceptance Criteria

### Technical & Functional
- [ ] Adjacency map (edges + transit window + confidence thresholds) is externally configurable - not hardcoded.
- [ ] All of V1-V8 pass.
- [ ] Confidence band is visible on both the event card and the Incident detail view - never hidden behind a tooltip.
- [ ] No UI or log text anywhere states or implies a "confirmed" or "same person" identity match.
- [ ] Code review confirms no appearance-embedding calls and no N-camera graph logic exist in this module (e.g., no botsort feature-extraction imports).
- [ ] The exact demo beat is reproducible on demand: Track exits CAM-01 -> reappears on CAM-02 within window -> Incident created, confidence HIGH, shown live on the dashboard.
- [ ] Storage governance and audit-trail behavior from the prior feature are unaffected - a correlated Incident still respects Hold/dismiss/purge rules exactly as a single-camera event would.
