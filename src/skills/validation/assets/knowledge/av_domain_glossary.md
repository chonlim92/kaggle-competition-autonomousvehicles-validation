# AV Domain Glossary — Autonomous Vehicles Validation

> **Purpose**: Grounds the AV Validation Orchestrator with domain terminology,
> validation rules, and common data quality patterns encountered in AV datasets.

---

## Core Terminology

| Term | Definition |
|------|-----------|
| **AV** | Autonomous Vehicle — a vehicle capable of sensing its environment and operating without human input. |
| **Ego Vehicle** | The AV whose sensors and logs are the primary data source in a recording. |
| **Scene** | A time-bounded recording segment (typically 20–60 seconds) from the ego vehicle's sensor suite. |
| **Timestamp** | Unix epoch time (microseconds) used to synchronise multi-modal sensor data. |
| **Frame** | A single discrete sample at one timestamp across all sensor modalities. |
| **Sweep** | One full 360° rotation of a LiDAR sensor (typically 10 Hz). |
| **Sample** | An annotated keyframe selected from a scene for labelling. |
| **Sample Annotation** | A 3D bounding box or segmentation mask applied to an object in a sample. |

---

## Sensor Modalities

| Modality | Description | Common Issues |
|----------|-------------|---------------|
| **LiDAR** | Point cloud data from laser range finder. | Dropout, reflective surfaces, rain artefacts. |
| **Camera (RGB)** | 2D image data from forward/surround cameras. | Overexposure, lens flare, misaligned timestamps. |
| **RADAR** | Radio detection and ranging for velocity estimation. | Ghost targets, multipath reflections. |
| **IMU** | Inertial Measurement Unit — acceleration and angular rate. | Drift, calibration offset. |
| **GNSS/GPS** | Global Navigation Satellite System — position. | Urban canyon errors, signal loss, spoofing. |
| **CAN Bus** | Vehicle Controller Area Network — speed, steering, throttle. | Bit errors, missing frames. |

---

## Annotation Standards

### 3D Bounding Box Fields
- `center_x`, `center_y`, `center_z` — object centroid in ego frame (metres)
- `width`, `length`, `height` — object dimensions (metres)
- `rotation_z` — yaw angle in radians `[-π, π]`
- `velocity_x`, `velocity_y` — object velocity in ego frame (m/s)
- `tracking_id` — unique per-object ID consistent across frames
- `category` — object class label

### Standard Object Categories
`vehicle.car`, `vehicle.truck`, `vehicle.bus`, `vehicle.motorcycle`,
`vehicle.bicycle`, `pedestrian.adult`, `pedestrian.child`,
`pedestrian.wheelchair`, `movable_object.barrier`, `movable_object.trafficcone`,
`static_object.bicycle_rack`, `animal`

---

## Validation Rules

### Critical (must fix before submission)
- `MISSING_LABEL` — annotated frame has no objects despite visible obstacles
- `INVALID_TIMESTAMP` — timestamp out of sequence or future-dated
- `SENSOR_DROPOUT` — LiDAR/Camera produces empty data for >3 consecutive frames
- `DUPLICATE_TRACKING_ID` — same `tracking_id` assigned to two different objects in one frame
- `OUT_OF_RANGE_COORDINATE` — bounding box centre outside plausible geographic bounds

### High (should fix)
- `TRUNCATED_SCENE` — scene duration < 5 seconds
- `INCONSISTENT_VELOCITY` — velocity change >15 m/s between consecutive frames (not physically plausible)
- `NEGATIVE_DIMENSION` — width/length/height ≤ 0
- `CATEGORY_MISMATCH` — object category changes between frames for same `tracking_id`

### Medium (investigate)
- `LOW_POINT_DENSITY` — LiDAR sweep returns <100 points per sweep
- `STALE_TIMESTAMP` — sensor timestamp unchanged for >2 consecutive frames
- `PARTIAL_ANNOTATION` — annotation present on some cameras but not all for same object

### Low (informational)
- `UNUSUAL_ASPECT_RATIO` — bounding box dimensions outside typical class distribution
- `RARE_CATEGORY` — category appears in <0.1% of the dataset

---

## PII in AV Data — Common Occurrences

The following PII types frequently appear in raw AV datasets and **must be redacted**
before any LLM processing:

| PII Type | Example Location |
|----------|-----------------|
| Driver name | CAN Bus operator fields, scene metadata |
| Vehicle Identification Number (VIN) | Vehicle metadata JSON |
| Licence Plate | Camera images (handled separately), metadata strings |
| GPS Home Address | Trip origin/destination fields |
| Phone Number | Emergency contact fields in operator logs |
| Email Address | Dataset submitter metadata |

---

## Coordinate Frames

| Frame | Description |
|-------|-------------|
| **Ego / Vehicle** | Origin at rear axle centre, +X forward, +Y left, +Z up |
| **Sensor** | Origin at sensor mounting point |
| **Global / Map** | Fixed world frame; typically UTM or WGS-84 |
| **Image** | 2D pixel coordinates, origin top-left |

---

## Kaggle Competition Specifics

- **Submission format**: JSONL with one record per scene
- **Primary metric**: Mean Average Precision (mAP) at IoU threshold 0.5
- **Secondary metric**: Average Translation Error (ATE), Average Scale Error (ASE)
- **Evaluation categories**: All 12 standard object categories weighted equally
- **Max submission size**: 500 MB compressed

---

*Last updated: 2026-06 | Maintain this glossary as the project evolves.*
