# Demo Execution Guide

The SIH PS187 system includes a headless simulator that injects synthetic tracks into the AI pipeline to demonstrate the intelligence rules without needing live video feeds or running heavy inference.

## How to Run the Core Validation Suite

1. Activate your environment:
   ```bash
   .\.venv\Scripts\activate
   ```

2. Run the simulator:
   ```bash
   $env:PYTHONPATH="."
   python -m simulator
   ```

## Included Scenarios

The test suite formally validates 10 edge cases required for a robust border surveillance product:
- **Normal pedestrian** (False-positive mitigation)
- **Normal vehicle** (False-positive mitigation)
- **Brief intrusion** (Dwell-time filtering)
- **Persistent intrusion** (Escalation to LOW/MEDIUM)
- **Night movement** (Time-based contextual rules)
- **Night + restricted zone** (MEDIUM risk combination)
- **Night + restricted zone + border direction** (HIGH risk combination)
- **Night + restricted zone + border direction + loitering** (CRITICAL/HIGH combination)
- **Object exits zone** (State machine transitions event to RESOLVED)
- **Same object remains in zone** (Event Deduplication avoids log spam)

If any of these scenarios fail, the CI/CD pipeline should block deployment.
