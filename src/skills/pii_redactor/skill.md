---
name: pii_redactor
description: Redacts personally identifiable information (PII) from AV operational logs.
---

# Goal

The `enterprise_av_security_pii_cleaner` is a **deterministic, regex-driven PII
sanitisation tool** for autonomous vehicle disengagement logs and safety driver field
notes. It operates without LLM inference, making it suitable as a **pre-processing
gate** that runs before any text reaches a language model.

It specifically targets the three PII categories most prevalent in AV operational logs:

| PII Category | Example Raw Form | Redacted Form |
|---|---|---|
| Human driver names | `Safety Driver: John Ramirez` | `Safety Driver: [DRIVER_REDACTED]` |
| Vehicle licence plates | `Unit plate: 7XYZ123` | `Unit plate: [PLATE_REDACTED]` |
| Decimal GPS coordinates | `pos=(37.7749, -122.4194)` | `pos=([GPS_REDACTED])` |

---

## JSON Input Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EnterpriseAVSecurityPIICleaner",
  "description": "Input schema for the enterprise_av_security_pii_cleaner tool.",
  "type": "object",
  "required": ["raw_log_text"],
  "additionalProperties": false,
  "properties": {
    "raw_log_text": {
      "type": "string",
      "description": "Raw AV disengagement log or safety driver field note text that may contain PII. Must be a UTF-8 string. Maximum length: 65,536 characters.",
      "minLength": 1,
      "maxLength": 65536
    }
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `raw_log_text` | `string` | ✅ Yes | Raw text from AV log ingestion pipeline containing potential driver names, licence plates, and/or GPS coordinates |

---

## JSON Output Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PIICleanerOutput",
  "type": "object",
  "properties": {
    "redacted_text": {
      "type": "string",
      "description": "The sanitised output with all detected PII replaced by typed placeholders."
    },
    "pii_found": {
      "type": "boolean",
      "description": "True if at least one PII entity was detected and redacted."
    },
    "redaction_summary": {
      "type": "object",
      "description": "Count of redactions per PII category.",
      "properties": {
        "driver_names": { "type": "integer" },
        "licence_plates": { "type": "integer" },
        "gps_coordinates": { "type": "integer" },
        "total": { "type": "integer" }
      }
    },
    "original_char_count": { "type": "integer" },
    "redacted_char_count": { "type": "integer" }
  }
}
```

---

## Redaction Placeholders

| PII Category | Placeholder Token |
|---|---|
| Human driver name | `[DRIVER_REDACTED]` |
| Vehicle licence plate | `[PLATE_REDACTED]` |
| Decimal GPS coordinate pair | `[GPS_REDACTED]` |

---

## Regex Patterns (Reference)

### Driver Names
Matches contextual name references introduced by known AV log prefixes:

```
Pattern family:
  (Safety\s+Driver|Driver|Operator|SD|Technician|Engineer)[:\s]+<Name>
  <Name> = Title? FirstName LastName  (e.g. "Mr. John Ramirez", "Alice Chen")
```

### Vehicle Licence Plates
Matches common North American and EU plate formats:

```
Pattern family:
  [A-Z0-9]{1,4}[-\s]?[A-Z0-9]{1,4}[-\s]?[A-Z0-9]{1,4}
  (contextually bounded by plate/unit/vehicle keywords)
```

### Decimal GPS Coordinates
Matches bare decimal degree pairs (lat/lon):

```
Pattern family:
  ±DD.DDDDDD, ±DDD.DDDDDD
  (with optional keyword prefixes: lat/lon/gps/pos/location/coord)
```

---

## Usage Example

```python
from src.skills.pii_redactor.enterprise_av_security_pii_cleaner import clean_pii

result = clean_pii(raw_log_text=(
    "Safety Driver: John Ramirez. Unit: 7ABC123. "
    "Disengagement at GPS 37.774900, -122.419400. "
    "Driver reported sensor occlusion at junction."
))

# result["redacted_text"]:
# "Safety Driver: [DRIVER_REDACTED]. Unit: [PLATE_REDACTED]. "
# "Disengagement at GPS [GPS_REDACTED]. "
# "Driver reported sensor occlusion at junction."

# result["redaction_summary"]:
# {"driver_names": 1, "licence_plates": 1, "gps_coordinates": 1, "total": 3}
```

---

## Security Notes

> [!IMPORTANT]
> This tool uses **deterministic regex** — no model inference, no network calls.
> It MUST be invoked on all raw log text before any LLM processing step (see `guardrails.txt` GR-LEAK-002).

> [!WARNING]
> Regex-based name detection relies on contextual prefixes. Standalone bare names
> without a recognised prefix (e.g. just `"Alice Chen"` mid-sentence) may not be
> caught. For higher recall, chain this tool with the Presidio-backed `redact_pii`
> skill for defence-in-depth coverage.

---

## Integration in Agent Pipeline

```
Raw AV Log Input
      │
      ▼
enterprise_av_security_pii_cleaner   ← this tool (deterministic, fast)
      │
      ▼
redact_pii (Presidio)                ← secondary sweep (NER-based)
      │
      ▼
root_agent (LLM processing)          ← clean text only reaches LLM
      │
      ▼
Output Guardrails (GR-LEAK-002)      ← final output scan
```

---

*Manifest version 1.0.0 — last updated 2026-06-20*
