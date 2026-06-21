"""
tests/evaluation/conftest.py

Shared pytest fixtures for the AV Validation Agent evaluation suite.

Fixtures defined here are available to all test files in `tests/evaluation/`
without needing an explicit import.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Generator

import pytest
from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY is available during tests
load_dotenv(
    dotenv_path=Path(__file__).parent.parent.parent / ".env",
    override=False,  # Don't override CI-injected env vars
)

# ── Paths ─────────────────────────────────────────────────────────────────────

DATASETS_DIR = Path(__file__).parent / "datasets"
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ── Config Fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def agent_config():
    """Return the validated AgentConfig for this test session."""
    from src.agent.config import get_config
    return get_config()


# ── PII Redactor Fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def pii_redactor(agent_config):
    """Return a PIIRedactor instance configured from .env."""
    from src.skills.pii_redactor.scripts.redactor import PIIRedactor
    return PIIRedactor(
        mode=agent_config.pii_redaction_mode,
        placeholder=agent_config.pii_redaction_placeholder,
    )


# ── Dataset Loader ────────────────────────────────────────────────────────────

def load_eval_dataset(filename: str) -> list[dict[str, Any]]:
    """
    Load a JSONL evaluation dataset from the datasets/ directory.

    Args:
        filename: Name of the .jsonl file (e.g. 'pii_redaction.jsonl')

    Returns:
        List of test case dicts.
    """
    path = DATASETS_DIR / filename
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


@pytest.fixture(scope="session")
def pii_eval_dataset() -> list[dict[str, Any]]:
    """PII redaction evaluation dataset."""
    return load_eval_dataset("pii_redaction.jsonl")


@pytest.fixture(scope="session")
def telemetry_eval_dataset() -> list[dict[str, Any]]:
    """Telemetry validation evaluation dataset."""
    return load_eval_dataset("telemetry_valid.jsonl")


@pytest.fixture(scope="session")
def labels_eval_dataset() -> list[dict[str, Any]]:
    """Label validation evaluation dataset."""
    return load_eval_dataset("labels_valid.jsonl")


# ── Skip markers ──────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow-running")
    config.addinivalue_line("markers", "integration: mark test as requiring live API")
    config.addinivalue_line("markers", "unit: mark test as a fast unit test")
