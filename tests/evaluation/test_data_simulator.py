import pytest
from unittest.mock import patch, MagicMock
from src.skills.pii_redactor.scripts.data_simulator import AVDisengagementLogSimulator

@patch("src.skills.pii_redactor.scripts.data_simulator.genai")
def test_data_simulator(mock_genai):
    mock_client = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "Simulated log generated."
    mock_client.models.generate_content.return_value = mock_response

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        simulator = AVDisengagementLogSimulator()

    result = simulator.generate_batch(count=1)

    assert len(result) == 1
    assert "log_text" in result[0]
    assert result[0]["log_text"] == "Simulated log generated."

    gps_lat, gps_lon = simulator._random_gps({"lat_range": (34.0, 34.1), "lon_range": (-118.5, -118.4)})
    assert isinstance(gps_lat, float)
    assert isinstance(gps_lon, float)



    # test generate directly
    res = simulator.generate()
    assert "log_text" in res
