"""
src/agent/agent.py

Root ADK 2.0 orchestrator agent for the Autonomous Vehicles Validation project.

This module defines `root_agent` — the entry point consumed by:
  - `adk web src/agent/`   (ADK Dev UI)
  - `adk run src/agent/`   (CLI runner)
  - Programmatic test harnesses in `tests/evaluation/`

Architecture
------------
root_agent (LlmAgent)
  ├── pii_redactor_tool    (FunctionTool wrapping PIIRedactorSkill)
  ├── validate_telemetry   (FunctionTool — placeholder, extend as needed)
  ├── validate_labels      (FunctionTool — placeholder, extend as needed)
  └── generate_report      (FunctionTool — placeholder, extend as needed)
"""

from __future__ import annotations

import structlog
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from src.agent.config import get_config
from src.agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from src.skills.pii_redactor.skill import redact_pii

logger = structlog.get_logger(__name__)

# ── Tool: PII Redactor ────────────────────────────────────────────────────────

pii_redactor_tool = FunctionTool(func=redact_pii)


# ── Placeholder Tools (extend these as the project grows) ─────────────────────

def validate_telemetry(record_id: str, telemetry_json: str) -> dict:  # type: ignore[return]
    """
    Validate sensor telemetry readings for a single AV record.

    Args:
        record_id: Unique identifier for the AV data record.
        telemetry_json: JSON string containing raw telemetry fields.

    Returns:
        Validation result dict with `issues` list and `severity` map.
    """
    # TODO: Implement telemetry range checks, dropout detection, timestamp gaps
    logger.info("validate_telemetry called", record_id=record_id)
    return {
        "record_id": record_id,
        "status": "not_implemented",
        "issues": [],
        "message": "Telemetry validation not yet implemented — extend this tool.",
    }


def validate_labels(record_id: str, labels_json: str) -> dict:  # type: ignore[return]
    """
    Validate annotation labels for a single AV record.

    Args:
        record_id: Unique identifier for the AV data record.
        labels_json: JSON string containing label/annotation data.

    Returns:
        Validation result dict with `issues` list and `severity` map.
    """
    # TODO: Implement label completeness, class distribution, IOU checks
    logger.info("validate_labels called", record_id=record_id)
    return {
        "record_id": record_id,
        "status": "not_implemented",
        "issues": [],
        "message": "Label validation not yet implemented — extend this tool.",
    }


def generate_report(validation_results: str) -> dict:  # type: ignore[return]
    """
    Aggregate individual validation results into a final Kaggle submission report.

    Args:
        validation_results: JSON string of combined telemetry + label results.

    Returns:
        Structured report dict ready for Kaggle submission.
    """
    # TODO: Aggregate results, compute severity breakdown, format for submission
    logger.info("generate_report called")
    return {
        "status": "not_implemented",
        "message": "Report generation not yet implemented — extend this tool.",
    }


validate_telemetry_tool = FunctionTool(func=validate_telemetry)
validate_labels_tool = FunctionTool(func=validate_labels)
generate_report_tool = FunctionTool(func=generate_report)


# ── Root Orchestrator Agent ───────────────────────────────────────────────────

cfg = get_config()

root_agent = LlmAgent(
    name="av_validation_orchestrator",
    model=cfg.orchestrator_model,
    description=(
        "Production-grade orchestrator for Kaggle Autonomous Vehicles Validation. "
        "Validates AV telemetry and label data, redacts PII, and produces "
        "structured quality reports."
    ),
    instruction=ORCHESTRATOR_SYSTEM_PROMPT,
    tools=[
        pii_redactor_tool,
        validate_telemetry_tool,
        validate_labels_tool,
        generate_report_tool,
    ],
)

logger.info(
    "AV Validation Orchestrator initialised",
    model=cfg.orchestrator_model,
    env=cfg.app_env,
)
