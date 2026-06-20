# Automated PII & Validation Test Report

## Summary
The testing suite executes evaluations against the entire agentic pipeline, including Kaggle competition metric preparation, PII redaction accuracy, and synthetic LLM data generation. This ensures that Autonomous Vehicle disengagement text remains highly secure before LLM inference.

- **Total Tests Run**: 34
- **Success Rate**: 100% (34 passed, 0 failures, 0 skipped)
- **Time to Complete**: 30.13s
- **Total Code Coverage**: 89%

## Coverage Highlights

| Module Name | Statements | Missing | Coverage | Notes |
|---|---|---|---|---|
| `src\agent\agent.py` | 18 | 0 | **100%** | Full coverage of ADK initialization |
| `src\agent\config.py` | 19 | 0 | **100%** | Environment and model constants verified |
| `src\skills\validation\label_validator.py` | 37 | 2 | **95%** | Verifies ADK 2.0 bounding boxes schemas |
| `src\skills\validation\telemetry_validator.py`| 35 | 1 | **97%** | Validates ADK physics engine telemetry |
| `src\skills\pii_redactor\enterprise_av_security_pii_cleaner.py`| 103 | 1 | **99%** | Robust deterministic PII sanitizer |
| `src\skills\pii_redactor\data_simulator.py` | 69 | 4 | **94%** | Synthetic generator for LLM testing |
| `src\agent\hooks.py` | 26 | 12 | **54%** | Newly added AgentHook validation |
| `src\agent\app.py` | 117 | 38 | **68%** | UI module ignored for backend coverage testing via pragma |
| `src\skills\kaggle\pipeline.py` | 34 | 4 | **88%** | API integration mock testing |

## Security Verification
1. **Pre-commit Secrets Verification**: Enabled via Yelp's `detect-secrets` and Git `pre-commit-hooks`.
2. **ADK PII Agent Hook**: Installed successfully in `src/agent/hooks.py` acting as an event-driven `before_turn` validator across both UI and Core ADK agent loops.

---
_Generated locally via pytest automated runs during Phase 17 Stabilization._
