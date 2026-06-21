import pytest
from unittest.mock import patch, MagicMock
from src.skills.pii_redactor.data_simulator import AVDisengagementLogSimulator

@patch("src.skills.pii_redactor.data_simulator.genai")
def test_data_simulator(mock_genai):
    mock_model = MagicMock()
    mock_genai.GenerativeModel.return_value = mock_model
    mock_response = MagicMock()
    mock_response.text = "Simulated log generated."
    mock_model.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        simulator = AVDisengagementLogSimulator()

    result = simulator.generate_batch(count=1)

    assert len(result) == 1
    assert "log_text" in result[0]
    assert result[0]["log_text"] == "Simulated log generated."

    gps = simulator._get_random_gps()
    assert "lat" in gps
    assert "lon" in gps

    plate = simulator._generate_vehicle_plate()
    assert isinstance(plate, str)
    assert len(plate) >= 6

    # test generate directly
    res = simulator.generate()
    assert "log_text" in res
