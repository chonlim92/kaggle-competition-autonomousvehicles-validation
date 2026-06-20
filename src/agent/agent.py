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
from src.skills.pii_redactor.enterprise_av_security_pii_cleaner import clean_pii

logger = structlog.get_logger(__name__)

# ── Tool: PII Redactor ────────────────────────────────────────────────────────

pii_redactor_tool = FunctionTool(func=clean_pii)


from src.skills.validation import validate_telemetry, validate_labels, generate_report
from src.skills.knowledge_retrieval import retrieve_knowledge

validate_telemetry_tool = FunctionTool(func=validate_telemetry)
validate_labels_tool = FunctionTool(func=validate_labels)
generate_report_tool = FunctionTool(func=generate_report)
retrieve_knowledge_tool = FunctionTool(func=retrieve_knowledge)


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
        retrieve_knowledge_tool,
    ],
)

# Phase 13: Embed safety rules and guardrails into agent context at startup
import os
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    with open(os.path.join(base_dir, "assets", "rules.txt"), "r", encoding="utf-8") as f:
        rules_text = f.read()
    with open(os.path.join(base_dir, "assets", "guardrails.txt"), "r", encoding="utf-8") as f:
        guardrails_text = f.read()
    
    root_agent.instruction += f"\n\n## Core Safety Rules\n{rules_text}\n\n## Guardrails\n{guardrails_text}"
except Exception as e:
    logger.warning("Failed to load assets into agent context", error=str(e))


logger.info(
    "AV Validation Orchestrator initialised",
    model=cfg.orchestrator_model,
    env=cfg.app_env,
)
