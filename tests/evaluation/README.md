# Evaluation Test Suite

This directory contains the **ADK 2.0 evaluation harness** for the AV Validation Orchestrator.

## Structure

```
tests/evaluation/
├── conftest.py               # Shared pytest fixtures (agent, config, sessions)
├── test_agent_eval.py        # Main evaluation test cases
├── datasets/                 # JSONL evaluation datasets
│   ├── pii_redaction.jsonl   # PII redactor unit eval cases
│   ├── telemetry_valid.jsonl # Telemetry validation eval cases
│   └── labels_valid.jsonl    # Label validation eval cases
└── README.md                 # This file
```

## Running Evaluations

```bash
# Run all evaluation tests
pytest tests/evaluation/ -v

# Run with coverage
pytest tests/evaluation/ -v --cov=src --cov-report=html

# Run only PII redaction evals
pytest tests/evaluation/ -v -k "pii"

# Run only agent integration evals
pytest tests/evaluation/ -v -k "agent"
```

## Dataset Format (JSONL)

Each line in a `.jsonl` dataset file is a JSON object:

```json
{
  "id": "unique-test-id",
  "input": "The input text or structured data",
  "expected_output": "The expected response",
  "tags": ["pii", "critical"],
  "metadata": {}
}
```

## Adding New Eval Cases

1. Add entries to the relevant `.jsonl` file in `datasets/`
2. Or create a new dataset file and register it in `conftest.py`
3. Write test functions in `test_agent_eval.py` referencing the dataset

## Metrics Tracked

- **PII Recall** — fraction of PII entities correctly detected and redacted
- **PII Precision** — fraction of redacted spans that were actually PII
- **Validation Accuracy** — fraction of issues correctly classified
- **Severity Agreement** — Cohen's κ between agent and ground-truth severity ratings
- **Response Latency** — P50 / P95 / P99 response time (ms)
