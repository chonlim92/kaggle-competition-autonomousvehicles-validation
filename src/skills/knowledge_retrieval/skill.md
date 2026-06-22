---
name: knowledge_retrieval
description: Retrieves domain knowledge, safety rules, and fleet history from local assets.
---

# Goals

The `knowledge_retrieval` skill is an essential tool for the orchestration agent to fetch necessary domain-specific knowledge, guardrails, and historical data required for auditing autonomous vehicle disengagement logs and sensor telemetry.

# Instructions

1. Use `retrieve_knowledge` to read specific knowledge assets by passing the document name.
2. Provide the retrieved content to the language model context to ensure compliance evaluations are grounded in the actual corporate rules and glossary definitions.

# Guides

- **Document Names**: Accepted documents include `rules.txt`, `fleet_history.txt`, `guardrails.txt`, or `knowledge/av_domain_glossary.md`.

# Tools (optional)

- `retrieve_knowledge`: Function to load text from the specified asset document.

# Assets (optional)

- `rules.txt`
- `fleet_history.txt`
- `guardrails.txt`
- `av_domain_glossary.md`

# References (optional)

- Input schema takes `document_name`.
- Output schema returns the full text content as a string.

# Examples (optional)

```python
from src.skills.knowledge_retrieval.scripts.knowledge_retrieval import retrieve_knowledge

rules = retrieve_knowledge("rules.txt")
print(rules)
```
