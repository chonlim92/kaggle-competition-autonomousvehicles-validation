---
name: validation
description: Evaluates and validates vehicle telemetry, guardrails, and labeled bounding boxes against safety constraints.
---

# Goals

This skill provides a suite of tools for validating autonomous vehicle disengagement logs and sensor telemetry against pre-defined safety guardrails and label annotations. The goal is to output formatted incident reports classifying events into CRITICAL, HIGH, or LOW severity breaches.

# Instructions

1. Use `validate_telemetry` to check for timestamp continuity and LiDAR/camera sensor dropout gaps. Pass the specific sensor readings to the tool to determine if `LOW_POINT_DENSITY` or `SENSOR_DROPOUT` thresholds are violated.
2. Use `validate_labels` to ensure all 2D and 3D bounding boxes are geometrically possible (e.g. no negative dimensions) and verify classification consistency across frames for matching tracking IDs.
3. If uncertain about specific domain terminology, use the `retrieve_knowledge_tool` to reference definitions from `av_domain_glossary.md` or thresholds from `rules.txt` and `guardrails.txt`.
4. Once telemetry and label constraints are verified, pass the collected incident data to `generate_report` to format the final Kaggle-compliant JSONL report, ensuring it classifies overall pipeline severity accurately.

# Guides

- **Telemetry Checks:** Always prioritize verifying timestamp sequence (`delta >= 0`). Any negative jump or jump > 500ms indicates a fatal recording dropout. For LiDAR, the point count per sweep must be ≥ 10,000 points.
- **Label Formatting:** Bounding boxes must have strictly positive width, height, and depth. A negative dimension is an instant data corruption failure (`NEGATIVE_DIMENSION`). 
- **Report Aggregation:** If ANY sensor fails a telemetry check, or a bounding box is impossible, the event escalates immediately to a CRITICAL severity. Otherwise, minor classification mismatches result in a HIGH severity. Ensure no PII leaks into the final report payload.

# Tools (optional)

- `validate_telemetry`: Checks telemetry continuity and values.
- `validate_labels`: Verifies 2D/3D bounding boxes.
- `generate_report`: Formats a compliance report based on incidents.
- `retrieve_knowledge_tool`: Provides access to domain glossary and history.

# Assets (optional)

- `av_domain_glossary.md`
- `fleet_history.txt`
- `guardrails.txt`
- `rules.txt`

# References (optional)

# Examples (optional)
