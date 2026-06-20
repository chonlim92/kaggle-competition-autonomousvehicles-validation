import json
import os
from pathlib import Path
import pytest

from google.adk.session import Session

# Try to import root_agent
try:
    from src.agent.agent import root_agent
except ImportError:
    root_agent = None

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"

def load_golden_dataset() -> list:
    if not DATASET_PATH.exists():
        return []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.mark.integration
@pytest.mark.parametrize("case", load_golden_dataset(), ids=lambda c: c["case_id"])
def test_golden_dataset_pii_redaction(case: dict) -> None:
    """
    Live LLM evaluation engine test against the golden dataset.
    Ensures that PII is redacted properly (trajectory + output token constraint).
    """
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set - skipping live evaluation")
    
    if root_agent is None:
        pytest.fail("Failed to import root_agent")

    input_text = case["input_text"]
    expected_trajectory = set(case["expected_trajectory"])
    forbidden_tokens = case["forbidden_tokens"]

    # Run the agent using ADK Session
    session = Session(agent=root_agent)
    
    # We ask the agent to validate the given raw log
    prompt = f"Please process and validate this raw log: {input_text}"
    response = session.run(prompt)
    
    final_output = response.text
    
    # 1. Audit Trajectory
    # We inspect the history of the session to check if the expected tools were called
    tool_calls = []
    for step in session.history:
        # Check tool calls inside the messages or steps
        if hasattr(step, "tool_calls") and step.tool_calls:
            for tc in step.tool_calls:
                tool_calls.append(tc.name)
        elif hasattr(step, "parts"):
            for part in step.parts:
                if hasattr(part, "function_call"):
                    tool_calls.append(part.function_call.name)
    
    called_tool_names = set(tool_calls)
    for expected_tool in expected_trajectory:
        assert expected_tool in called_tool_names, f"Agent failed to call required tool: {expected_tool}"

    # 2. Audit Output Tokens
    # We strictly verify that NO forbidden token leaked into the final output
    leaks = []
    for token in forbidden_tokens:
        if token in final_output:
            leaks.append(token)
            
    assert not leaks, f"Strict Output Token Verification Failed! The following PII tokens leaked: {leaks}\nFinal Output: {final_output}"
