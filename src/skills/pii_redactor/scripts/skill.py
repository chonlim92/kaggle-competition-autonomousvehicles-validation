"""
src/skills/pii_redactor/skill.py

ADK FunctionTool interface for the PII Redactor skill.

This module exposes `redact_pii` — a plain Python function with a typed
signature that the ADK `FunctionTool` wrapper can introspect to auto-generate
the JSON schema presented to the LLM.

The function is a thin adapter over `PIIRedactor` that reads configuration
from the shared `AgentConfig` singleton, ensuring the skill honours the
same environment-driven settings as the rest of the agent system.
"""

from __future__ import annotations

import structlog

from src.agent.config import get_config
from src.skills.pii_redactor.scripts.redactor import PIIRedactor, RedactionResult

logger = structlog.get_logger(__name__)

# Singleton redactor — instantiated once at module load with config from .env
_cfg = get_config()
_redactor = PIIRedactor(
    mode=_cfg.pii_redaction_mode,
    placeholder=_cfg.pii_redaction_placeholder,
)


def redact_pii(text: str) -> dict:
    """
    Detect and redact Personally Identifiable Information (PII) from text.

    Use this tool on any free-text or unstructured input before passing it
    to the LLM for analysis. The tool will replace PII such as names, email
    addresses, phone numbers, Vehicle Identification Numbers (VINs), and
    licence plate numbers with a safe placeholder.

    Args:
        text: The raw text string that may contain PII. Can be a log entry,
              sensor description, driver note, or any unstructured field
              from the AV dataset.

    Returns:
        A dictionary with:
          - redacted_text (str): The text with all detected PII replaced.
          - pii_found (bool): True if any PII was detected.
          - detected_entities (list): Metadata about each detected PII entity
            (type, position, confidence score).
          - original_length (int): Character count of the original text.
          - redacted_length (int): Character count of the redacted text.
    """
    logger.debug("redact_pii invoked", input_length=len(text))

    result: RedactionResult = _redactor.redact(text)

    return {
        "redacted_text": result.redacted_text,
        "pii_found": result.pii_found,
        "detected_entities": result.detected_entities,
        "original_length": len(result.original_text),
        "redacted_length": len(result.redacted_text),
    }
