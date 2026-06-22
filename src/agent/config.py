"""
src/agent/config.py

Centralised runtime configuration loader for the AV Validation Agent.
Reads from environment variables (populated via .env) and exposes a
strongly-typed `AgentConfig` Pydantic model consumed throughout the project.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load .env from project root (walks up if needed)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


class AgentConfig(BaseModel):
    """Validated runtime configuration for the AV Validation Agent."""

    # ── Google AI ─────────────────────────────────────────────────────────────
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    google_genai_use_enterprise: bool = Field(
        default=False,
        description="Route requests through Vertex AI Enterprise endpoint",
    )

    # ── Model Selection ───────────────────────────────────────────────────────
    orchestrator_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model ID used by the orchestrator agent",
    )

    # ── Runtime ───────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    # ── Evaluation ────────────────────────────────────────────────────────────
    eval_dataset_path: str = Field(default="tests/evaluation/datasets/")

    # ── PII Redactor ─────────────────────────────────────────────────────────
    pii_redaction_mode: Literal["mask", "redact", "tokenize"] = Field(default="mask")
    pii_redaction_placeholder: str = Field(default="[REDACTED]")

    @field_validator("google_genai_use_enterprise", mode="before")
    @classmethod
    def coerce_bool(cls, v: object) -> bool:
        """Accept 'TRUE'/'FALSE' string values from environment."""
        if isinstance(v, str):
            return v.upper() == "TRUE"
        return bool(v)

    model_config = {"frozen": True}


@lru_cache(maxsize=1)
def get_config() -> AgentConfig:
    """Return a cached, validated AgentConfig instance."""
    return AgentConfig(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "dummy_key_for_testing"),
        google_genai_use_enterprise=os.getenv("GOOGLE_GENAI_USE_ENTERPRISE", "FALSE"),
        orchestrator_model=os.getenv("ORCHESTRATOR_MODEL", "gemini-2.5-flash"),
        app_env=os.getenv("APP_ENV", "development"),  # type: ignore[arg-type]
        log_level=os.getenv("LOG_LEVEL", "INFO"),  # type: ignore[arg-type]
        eval_dataset_path=os.getenv("EVAL_DATASET_PATH", "tests/evaluation/datasets/"),
        pii_redaction_mode=os.getenv("PII_REDACTION_MODE", "mask"),  # type: ignore[arg-type]
        pii_redaction_placeholder=os.getenv("PII_REDACTION_PLACEHOLDER", "[REDACTED]"),
    )
