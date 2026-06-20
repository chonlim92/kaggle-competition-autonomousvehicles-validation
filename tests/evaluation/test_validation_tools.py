import json
import pytest
from pathlib import Path

from src.skills.validation.telemetry_validator import validate_telemetry
from src.skills.validation.label_validator import validate_labels

DATASETS_DIR = Path(__file__).parent / "datasets"

def load_jsonl(filename: str):
    data = []
    filepath = DATASETS_DIR / filename
    if not filepath.exists():
        return data
    with open(filepath, "r") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

TELEMETRY_CASES = load_jsonl("telemetry_valid.jsonl")
LABEL_CASES = load_jsonl("labels_valid.jsonl")

@pytest.mark.unit
@pytest.mark.parametrize("case", TELEMETRY_CASES, ids=[c["id"] for c in TELEMETRY_CASES])
def test_validate_telemetry(case):
    input_data = case["input"]
    expected_issues = set(case.get("expected_issues", []))
    
    # Run the tool
    record_id = input_data.get("record_id", "test")
    result = validate_telemetry(record_id, json.dumps(input_data))
    
    # Assert
    actual_issues = set(result.get("issues", []))
    assert actual_issues == expected_issues, f"Expected {expected_issues}, got {actual_issues}"
    
    if expected_issues:
        assert result["status"] == "failed"
    else:
        assert result["status"] == "passed"

@pytest.mark.unit
@pytest.mark.parametrize("case", LABEL_CASES, ids=[c["id"] for c in LABEL_CASES])
def test_validate_labels(case):
    input_data = case["input"]
    expected_issues = set(case.get("expected_issues", []))
    
    # Run the tool
    record_id = input_data.get("record_id", "test")
    result = validate_labels(record_id, json.dumps(input_data))
    
    # Assert
    actual_issues = set(result.get("issues", []))
    assert actual_issues == expected_issues, f"Expected {expected_issues}, got {actual_issues}"
    
    if expected_issues:
        assert result["status"] == "failed"
    else:
        assert result["status"] == "passed"
