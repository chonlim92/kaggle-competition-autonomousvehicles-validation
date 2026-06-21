import json
import structlog

logger = structlog.get_logger(__name__)

def validate_labels(record_id: str, labels_json: str) -> dict:
    """
    Validate annotation labels for a single AV record.

    Args:
        record_id: Unique identifier for the AV data record.
        labels_json: JSON string containing label/annotation data.

    Returns:
        Validation result dict with `issues` list and `severity` map.
    """
    logger.info("validate_labels called", record_id=record_id)

    try:
        data = json.loads(labels_json)
    except json.JSONDecodeError as e:
        return {
            "record_id": record_id,
            "status": "failed",
            "issues": ["JSON_PARSE_ERROR"],
            "severity": {"JSON_PARSE_ERROR": "CRITICAL"},
            "message": f"Failed to parse labels JSON: {e}"
        }

    issues = []
    severities = {}

    annotations = data.get("annotations", [])

    # Check for empty annotations
    if not annotations:
        issues.append("MISSING_LABEL")
        severities["MISSING_LABEL"] = "CRITICAL"

    tracking_id_categories = {}

    for ann in annotations:
        # Check for negative dimensions
        width = ann.get("width", 0)
        length = ann.get("length", 0)
        height = ann.get("height", 0)
        if width < 0 or length < 0 or height < 0:
            if "NEGATIVE_DIMENSION" not in issues:
                issues.append("NEGATIVE_DIMENSION")
                severities["NEGATIVE_DIMENSION"] = "HIGH"

        # Check for category consistency across tracking IDs
        track_id = ann.get("tracking_id")
        cat = ann.get("category")
        if track_id and cat:
            if track_id in tracking_id_categories:
                if tracking_id_categories[track_id] != cat:
                    if "CATEGORY_MISMATCH" not in issues:
                        issues.append("CATEGORY_MISMATCH")
                        severities["CATEGORY_MISMATCH"] = "HIGH"
            else:
                tracking_id_categories[track_id] = cat

    status = "failed" if issues else "passed"

    return {
        "record_id": record_id,
        "status": status,
        "issues": issues,
        "severity": severities,
        "message": f"Label validation completed with {len(issues)} issues."
    }
