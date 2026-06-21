import pytest
from unittest.mock import patch, MagicMock
from src.agent.app import generate_synthetic_log, run_secure_validation, execute_evaluation_suite

@patch("src.agent.app._simulator")
def test_generate_synthetic_log_success(mock_sim):
    mock_sim.generate_batch.return_value = [{
        "log_text": "Sample log",
        "metadata": {
            "injected_pii": {
                "case_id": "EVT-123456",
                "driver_name": "Test",
                "plate_primary": "ABC",
                "plate_witness": "DEF",
                "gps_primary": {"lat": 1, "lon": 2, "region": "X"},
                "gps_secondary": {"lat": 3, "lon": 4, "region": "Y"}
            },
            "fleet_unit": "U1",
            "scenario": "Scen1"
        },
        "model": "test-model"
    }]
    log_text, meta, map_html = generate_synthetic_log()
    assert "Sample log" in log_text
    assert "Test" in meta

@patch("src.agent.app._simulator", None)
def test_generate_synthetic_log_no_sim():
    log_text, meta, map_html = generate_synthetic_log()
    assert "Simulator unavailable" in log_text

@patch("src.agent.app.asyncio.run")
@patch("src.agent.app._ADK_AVAILABLE", True)
@patch("src.agent.app._adk_runner", True)
def test_run_secure_validation(mock_run):
    mock_run.return_value = "ADK Response"
    banner, context, report, map_html = run_secure_validation("GPS(1.0, 2.0)", "sess1")
    assert "PII Sanitisation Complete" in banner
    assert "[GPS_REDACTED]" in context
    assert "ADK Response" in report

def test_run_secure_validation_empty():
    banner, context, report, map_html = run_secure_validation("   ", "sess1")
    assert "No input provided" in banner

from src.agent.app import generate_synthetic_log, run_secure_validation, execute_evaluation_suite, _run_adk_agent, _init_session_id
import asyncio

def test_init_session_id():
    sid = _init_session_id()
    assert isinstance(sid, str)
    assert len(sid) > 10

@patch("src.agent.app._session_service")
@patch("src.agent.app._adk_runner")
def test_run_adk_agent(mock_runner, mock_session_service):
    from unittest.mock import AsyncMock
    mock_session_service.create_session = AsyncMock()
    mock_session_service.get_session = AsyncMock()
    # Mock the async generator
    async def mock_run_async(*args, **kwargs):
        class MockPart:
            text = "adk response"
        class MockContent:
            role = "model"
            parts = [MockPart()]
        class MockEvent:
            content = MockContent()
        yield MockEvent()
    
    mock_runner.run_async.side_effect = mock_run_async
    
    response = asyncio.run(_run_adk_agent("test", "sess1"))
    assert response == "adk response"

def test_run_adk_agent_not_initialized():
    with patch("src.agent.app._adk_runner", None):
        res = asyncio.run(_run_adk_agent("msg", "sess"))
        assert "not initialised" in res

    result = execute_evaluation_suite()
    assert "AV VALIDATION AGENT" in result
    assert "SUITE 2 — ENTERPRISE CLEANER SMOKE TESTS" in result
