import pytest
from src.skills.pii_redactor.enterprise_av_security_pii_cleaner import clean_pii

def test_enterprise_av_security_pii_cleaner():
    # Test GPS
    raw_text_1 = "GPS(37.774900, -122.419400)"
    result = clean_pii(raw_text_1)
    assert result["pii_found"] is True
    assert "[GPS_REDACTED]" in result["redacted_text"]

    # Test Plate
    raw_text_2 = "plate: 7XYZ123"
    result = clean_pii(raw_text_2)
    assert result["pii_found"] is True
    assert "[PLATE_REDACTED]" in result["redacted_text"]

    # Test Name
    raw_text_3 = "Safety Driver: John Doe"
    result = clean_pii(raw_text_3)
    assert result["pii_found"] is True
    assert "[DRIVER_REDACTED]" in result["redacted_text"]

    # Empty
    assert clean_pii("")["pii_found"] is False
