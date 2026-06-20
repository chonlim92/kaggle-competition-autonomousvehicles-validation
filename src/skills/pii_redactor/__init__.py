"""
src/skills/pii_redactor/__init__.py

PII Redactor skill package.
Exposes the `redact_pii` function as the primary ADK FunctionTool interface.
"""

from src.skills.pii_redactor.skill import redact_pii

__all__ = ["redact_pii"]
