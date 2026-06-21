---
name: pii_redactor
description: Redacts personally identifiable information (PII) from AV operational logs.
---

# Goals

The `enterprise_av_security_pii_cleaner` is a deterministic, regex-driven PII sanitisation tool for autonomous vehicle disengagement logs and safety driver field notes. It operates without LLM inference, making it suitable as a pre-processing gate that runs before any text reaches a language model.

# Instructions

1. Retrieve the raw disengagement log text from the data pipeline or user input.
2. Immediately pass the raw text through the `enterprise_av_security_pii_cleaner` tool before feeding any text to downstream LLMs. This is mandatory per `GR-LEAK-002`.
3. Check the returned output schema for `pii_found`. If true, the `redaction_summary` will detail exactly how many driver names, plates, and GPS coordinates were intercepted.
4. Use the `redacted_text` string securely in subsequent prompts. The raw text must be permanently discarded.

# Guides

- **Coverage Scope**: It specifically targets the three PII categories most prevalent in AV operational logs: Human driver names, Vehicle licence plates, and Decimal GPS coordinates.
- **Regex Limitations**: Regex-based name detection relies on contextual prefixes (e.g., "Safety Driver: John"). Standalone bare names without a recognised prefix may not be caught deterministicly.
- **Defence-in-Depth**: For highest recall and true compliance, this deterministic tool must be run first, but can optionally be chained with the Presidio-backed `redact_pii` NER skill for defence-in-depth coverage if bare names are suspected.
- **Placeholders**: The tool replaces sensitive strings with static typed tags like `[DRIVER_REDACTED]`, `[PLATE_REDACTED]`, and `[GPS_REDACTED]`.

# Tools (optional)

- `enterprise_av_security_pii_cleaner`: Deterministic regex cleaner.
- `redact_pii`: Presidio-backed NER redaction.
- `data_simulator`: Generates synthetic logs for testing.

# Assets (optional)

# References (optional)

- Input schema takes `raw_log_text`.
- Output schema returns `redacted_text`, `pii_found`, `redaction_summary`.

# Examples (optional)

```python
from src.skills.pii_redactor.scripts.enterprise_av_security_pii_cleaner import clean_pii

result = clean_pii(raw_log_text="Safety Driver: John Ramirez. Unit: 7ABC123. Disengagement at GPS 37.774900, -122.419400.")
print(result["redacted_text"])
# "Safety Driver: [DRIVER_REDACTED]. Unit: [PLATE_REDACTED]. Disengagement at [GPS_REDACTED]."
```
