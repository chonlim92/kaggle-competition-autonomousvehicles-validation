import json
import structlog

logger = structlog.get_logger(__name__)

def validate_telemetry(record_id: str, telemetry_json: str) -> dict:
    """
    Validate sensor telemetry readings for a single AV record.

    Args:
        record_id: Unique identifier for the AV data record.
        telemetry_json: JSON string containing raw telemetry fields.

    Returns:
        Validation result dict with `issues` list and `severity` map.
    """
    logger.info("validate_telemetry called", record_id=record_id)

    try:
        data = json.loads(telemetry_json)
    except json.JSONDecodeError as e:
        return {
            "record_id": record_id,
            "status": "failed",
            "issues": ["JSON_PARSE_ERROR"],
            "severity": {"JSON_PARSE_ERROR": "CRITICAL"},
            "message": f"Failed to parse telemetry JSON: {e}"
        }

    issues = []
    severities = {}

    # LiDAR check (AV-REG-102 MOT: >= 10,000 points/sweep)
    lidar_points = data.get("lidar_points_per_sweep")
    if lidar_points is not None and lidar_points < 10000:
        issues.append("LOW_POINT_DENSITY")
        severities["LOW_POINT_DENSITY"] = "CRITICAL"

    # Camera FPS check (AV-REG-102 MOT)
    camera_fps = data.get("camera_fps")
    if camera_fps is not None and camera_fps == 0:
        issues.append("SENSOR_DROPOUT")
        severities["SENSOR_DROPOUT"] = "CRITICAL"

    # Timestamp gap anomaly
    timestamp_gap_ms = data.get("timestamp_gap_ms")
    if timestamp_gap_ms is not None and timestamp_gap_ms > 500:
        if "SENSOR_DROPOUT" not in issues:
            issues.append("SENSOR_DROPOUT")
            severities["SENSOR_DROPOUT"] = "CRITICAL"

    # Velocity anomaly check
    velocity_delta = data.get("velocity_delta_ms")
    if velocity_delta is not None and velocity_delta > 10.0:
        issues.append("INCONSISTENT_VELOCITY")
        severities["INCONSISTENT_VELOCITY"] = "HIGH"

    status = "failed" if issues else "passed"

    return {
        "record_id": record_id,
        "status": status,
        "issues": issues,
        "severity": severities,
        "message": f"Telemetry validation completed with {len(issues)} issues."
    }
