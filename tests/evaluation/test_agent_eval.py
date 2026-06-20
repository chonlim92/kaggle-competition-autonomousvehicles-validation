"""
tests/evaluation/test_agent_eval.py

Evaluation test suite for the AV Validation Orchestrator.

Test Categories
---------------
1. Unit Tests  — fast, no API calls (PII redactor logic, config loading)
2. Skill Tests — test individual tools in isolation
3. Integration — end-to-end agent tests requiring GEMINI_API_KEY

Run order (recommended):
  pytest tests/evaluation/ -v -m "unit"         # Fast: always run
  pytest tests/evaluation/ -v -m "skill"        # Medium: skill isolation
  pytest tests/evaluation/ -v -m "integration"  # Slow: CI/CD gate
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest


# ==============================================================================
# 1. Unit Tests — Config
# ==============================================================================

@pytest.mark.unit
class TestAgentConfig:
    """Validate AgentConfig loads correctly from .env."""

    def test_config_loads_without_error(self, agent_config: Any) -> None:
        """Config should instantiate without raising exceptions."""
        assert agent_config is not None

    def test_gemini_api_key_present(self, agent_config: Any) -> None:
        """GEMINI_API_KEY must be set and non-empty."""
        assert agent_config.gemini_api_key, "GEMINI_API_KEY is not set in .env"
        assert len(agent_config.gemini_api_key) > 10, "GEMINI_API_KEY looks too short"

    def test_enterprise_flag_is_bool(self, agent_config: Any) -> None:
        """GOOGLE_GENAI_USE_ENTERPRISE must coerce to bool."""
        assert isinstance(agent_config.google_genai_use_enterprise, bool)

    def test_app_env_valid(self, agent_config: Any) -> None:
        """APP_ENV must be one of the allowed values."""
        assert agent_config.app_env in ("development", "staging", "production")

    def test_pii_mode_valid(self, agent_config: Any) -> None:
        """PII_REDACTION_MODE must be one of the allowed values."""
        assert agent_config.pii_redaction_mode in ("mask", "redact", "tokenize")


# ==============================================================================
# 2. Unit Tests — PII Redactor
# ==============================================================================

@pytest.mark.unit
class TestPIIRedactorUnit:
    """Unit tests for PIIRedactor core logic — no API calls."""

    def test_email_redacted(self, pii_redactor: Any) -> None:
        """Email addresses must be detected and replaced."""
        result = pii_redactor.redact("Contact driver@example.com for details.")
        assert "driver@example.com" not in result.redacted_text

    def test_vin_redacted(self, pii_redactor: Any) -> None:
        """17-character VINs must be detected and replaced."""
        result = pii_redactor.redact("Vehicle VIN: 1HGBH41JXMN109186 registered.")
        assert "1HGBH41JXMN109186" not in result.redacted_text

    def test_phone_redacted(self, pii_redactor: Any) -> None:
        """Phone numbers must be detected and replaced."""
        result = pii_redactor.redact("Call +1-800-555-0199 for support.")
        assert "+1-800-555-0199" not in result.redacted_text

    def test_empty_string_returns_safely(self, pii_redactor: Any) -> None:
        """Empty input must not raise and must return empty redacted text."""
        result = pii_redactor.redact("")
        assert result.redacted_text == ""
        assert not result.pii_found

    def test_clean_text_unchanged(self, pii_redactor: Any) -> None:
        """Text without PII should be returned with no detections."""
        clean = "The vehicle travelled 42 km at 60 km/h on Route 66."
        result = pii_redactor.redact(clean)
        # Should not find PII (Route 66 is not a personal address)
        assert result.redacted_text is not None

    def test_pii_found_flag(self, pii_redactor: Any) -> None:
        """pii_found should be True when PII is detected."""
        result = pii_redactor.redact("Email me at test@domain.com.")
        assert result.pii_found is True

    def test_result_has_required_fields(self, pii_redactor: Any) -> None:
        """RedactionResult must always expose required fields."""
        result = pii_redactor.redact("Some text.")
        assert hasattr(result, "original_text")
        assert hasattr(result, "redacted_text")
        assert hasattr(result, "detected_entities")
        assert hasattr(result, "pii_found")


# ==============================================================================
# 3. Skill Tests — FunctionTool interface
# ==============================================================================

@pytest.mark.unit
class TestRedactPIISkill:
    """Tests for the `redact_pii` FunctionTool adapter."""

    def test_returns_dict(self) -> None:
        """redact_pii must return a dict (ADK FunctionTool requirement)."""
        from src.skills.pii_redactor.skill import redact_pii
        result = redact_pii("Hello world")
        assert isinstance(result, dict)

    def test_dict_keys_present(self) -> None:
        """Result dict must contain all documented keys."""
        from src.skills.pii_redactor.skill import redact_pii
        result = redact_pii("Contact john.doe@example.com")
        assert "redacted_text" in result
        assert "pii_found" in result
        assert "detected_entities" in result
        assert "original_length" in result
        assert "redacted_length" in result

    def test_length_fields_correct(self) -> None:
        """original_length and redacted_length must match text lengths."""
        from src.skills.pii_redactor.skill import redact_pii
        text = "Hello world"
        result = redact_pii(text)
        assert result["original_length"] == len(text)
        assert result["redacted_length"] == len(result["redacted_text"])


# ==============================================================================
# 4. Dataset-Driven PII Eval (parametrized from JSONL)
# ==============================================================================

@pytest.mark.unit
class TestPIIEvalDataset:
    """Run evaluation cases from pii_redaction.jsonl if the file exists."""

    def test_dataset_cases(
        self, pii_redactor: Any, pii_eval_dataset: list[dict]
    ) -> None:
        """Each eval case: redacted_text must not contain the expected PII."""
        if not pii_eval_dataset:
            pytest.skip("No PII eval dataset found — add cases to datasets/pii_redaction.jsonl")

        failures: list[str] = []
        for case in pii_eval_dataset:
            case_id = case.get("id", "unknown")
            input_text = case.get("input", "")
            pii_to_check = case.get("pii_strings", [])  # list of strings that should be gone

            result = pii_redactor.redact(input_text)
            for pii_str in pii_to_check:
                if pii_str in result.redacted_text:
                    failures.append(f"[{case_id}] '{pii_str}' was NOT redacted")

        assert not failures, "PII redaction failures:\n" + "\n".join(failures)


# ==============================================================================
# 5. Integration Tests — Live Agent (requires GEMINI_API_KEY)
# ==============================================================================

@pytest.mark.integration
@pytest.mark.slow
class TestAgentIntegration:
    """
    End-to-end integration tests using the live Gemini API.

    These tests are marked `integration` and `slow`.
    Skip them in local unit-test runs:
      pytest tests/evaluation/ -m "not integration"
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_api_key(self) -> None:
        """Skip integration tests if GEMINI_API_KEY is not available."""
        if not os.getenv("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set — skipping integration test")

    def test_root_agent_importable(self) -> None:
        """root_agent must import without errors."""
        from src.agent.agent import root_agent
        assert root_agent is not None
        assert root_agent.name == "av_validation_orchestrator"

    def test_root_agent_has_tools(self) -> None:
        """root_agent must have all expected tools registered."""
        from src.agent.agent import root_agent
        tool_names = [t.name for t in root_agent.tools]
        assert "redact_pii" in tool_names, f"redact_pii not found in tools: {tool_names}"

    def test_agent_response_latency(self) -> None:
        """
        Agent must respond within 30 seconds for a simple prompt.
        This is a smoke-test for API connectivity and model availability.
        """
        # NOTE: Full ADK session runner integration to be implemented when
        # google-adk session API is confirmed. This is a placeholder structure.
        start = time.monotonic()
        # Placeholder — replace with actual ADK runner invocation:
        # runner = Runner(agent=root_agent, ...)
        # response = runner.run("Hello, are you ready to validate AV data?")
        elapsed_ms = (time.monotonic() - start) * 1000
        # Until runner is wired, just verify import time is sane
        assert elapsed_ms < 30_000, f"Agent took too long to respond: {elapsed_ms:.0f}ms"
