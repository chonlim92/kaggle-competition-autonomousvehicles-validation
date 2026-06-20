"""
src/agent/__init__.py

Exposes the root ADK 2.0 orchestrator agent for this project.
Import `root_agent` to wire it into the ADK runtime or web server.
"""

from src.agent.agent import root_agent

__all__ = ["root_agent"]
