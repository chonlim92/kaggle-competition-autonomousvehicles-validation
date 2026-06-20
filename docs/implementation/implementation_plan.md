# Implementation Plan — AV Validation Agent

## Goal

Initialize a **production-grade ADK 2.0 agent** for the Kaggle Autonomous Vehicles Validation
competition, starting from an empty cloned repository. The agent must be fully operable from
day one, with no manual file creation required from the developer.

---

## Background

The project is based on the Google ADK (Agent Developer Kit) 2.0 framework.
It uses Gemini as the underlying LLM and is structured to validate autonomous
vehicle telemetry and annotation data submitted as part of a Kaggle competition.

Key non-functional requirements:
- **Privacy by default** — PII must be redacted before LLM processing
- **Auditability** — every validation finding is traceable to a record ID
- **Testability** — layered test pyramid with dataset-driven evaluation
- **Zero secrets in git** — `.env` protected by `.gitignore` from the first commit

---

## Proposed Changes

### Root Scaffolding

#### [NEW] `.env`
Local-only secrets file. Contains `GEMINI_API_KEY` and `GOOGLE_GENAI_USE_ENTERPRISE=FALSE`.
Protected by `.gitignore` — never committed.

#### [NEW] `.env.example`
Committed template for team onboarding. Documents every supported env variable.

#### [NEW] `.gitignore`
Covers Python build artefacts, virtual environments, IDE configs, ADK runtime
sessions, and critically the `.env` file.

#### [NEW] `README.md`
Top-level project documentation: quickstart, directory tree, environment variable
reference, and architecture overview.

#### [NEW] `pyproject.toml`
Single-file dependency and build configuration. Key dependencies:
- `google-adk>=2.0.0` — ADK 2.0 runtime
- `google-generativeai>=0.8.0` — Gemini SDK
- `presidio-analyzer` + `presidio-anonymizer` — PII detection engine
- `pydantic>=2.7.0` — runtime config validation
- `structlog>=24.0.0` — structured logging
- Dev extras: `pytest`, `ruff`, `mypy`, `pre-commit`

---

### Component: Core Orchestrator Agent (`src/agent/`)

#### [NEW] `src/agent/__init__.py`
Package init — exports `root_agent` as the ADK entry point.

#### [NEW] `src/agent/config.py`
Frozen Pydantic `AgentConfig` model loaded from environment variables via
`python-dotenv`. Cached as a singleton with `@lru_cache`. Fields:
- `gemini_api_key`, `google_genai_use_enterprise`
- `orchestrator_model` (default: `gemini-2.0-flash`)
- `app_env`, `log_level`
- `pii_redaction_mode`, `pii_redaction_placeholder`
- `eval_dataset_path`

#### [NEW] `src/agent/prompts.py`
Versioned system prompts stored separately from agent wiring:
- `ORCHESTRATOR_SYSTEM_PROMPT` — full AV expert persona, operating principles,
  tool usage guidelines, and required JSON output format
- `PII_REDACTOR_TASK_PROMPT` — sub-task prompt for PII scanning

#### [NEW] `src/agent/agent.py`
Root `LlmAgent` (`root_agent`) with four `FunctionTool` slots:
| Tool | Status |
|------|--------|
| `redact_pii` | ✅ Implemented (via PII Redactor skill) |
| `validate_telemetry` | 🔲 Placeholder — extend with range/dropout checks |
| `validate_labels` | 🔲 Placeholder — extend with IOU/class checks |
| `generate_report` | 🔲 Placeholder — extend with aggregation logic |

---

### Component: PII Redactor Skill (`src/skills/pii_redactor/`)

#### [NEW] `src/skills/pii_redactor/__init__.py`
Package init — exports `redact_pii`.

#### [NEW] `src/skills/pii_redactor/redactor.py`
Core `PIIRedactor` class with:
- **Primary engine**: Microsoft Presidio (`presidio-analyzer` + `presidio-anonymizer`)
- **Custom recognizers**: VIN (17-char regex, score 0.85) + Licence Plate (EU/US pattern)
- **Fallback**: Regex-only redaction when Presidio is not installed
- **Three modes**: `mask` (placeholder), `redact` (`<ENTITY_TYPE>` tag), `tokenize` (SHA-256 hash)
- Returns `RedactionResult` dataclass with `redacted_text`, `detected_entities`, `pii_found`

#### [NEW] `src/skills/pii_redactor/skill.py`
ADK `FunctionTool` adapter. Thin wrapper over `PIIRedactor` with:
- Rich docstring for LLM JSON schema auto-generation
- Reads config from the shared `AgentConfig` singleton
- Returns plain `dict` (ADK requirement)

---

### Component: Knowledge Assets (`assets/`)

#### [NEW] `assets/README.md`
Documents the knowledge asset structure and usage pattern.

#### [NEW] `assets/knowledge/av_domain_glossary.md`
Comprehensive AV domain reference covering:
- Core terminology (ego vehicle, scene, frame, sweep, sample)
- Sensor modalities (LiDAR, Camera, RADAR, IMU, GNSS, CAN Bus)
- Annotation standards (3D bounding box fields, 12 standard categories)
- Validation rules by severity (CRITICAL / HIGH / MEDIUM / LOW)
- PII types common in AV datasets
- Coordinate frame conventions
- Kaggle competition specifics (mAP@0.5, ATE, ASE, submission format)

---

### Component: Evaluation Suite (`tests/evaluation/`)

#### [NEW] `tests/evaluation/conftest.py`
Shared pytest fixtures:
- `agent_config` (session-scoped) — validated `AgentConfig`
- `pii_redactor` (session-scoped) — `PIIRedactor` instance
- `pii_eval_dataset`, `telemetry_eval_dataset`, `labels_eval_dataset` — JSONL loaders
- Custom pytest markers: `unit`, `integration`, `slow`

#### [NEW] `tests/evaluation/test_agent_eval.py`
Four test classes:
1. `TestAgentConfig` — validates Pydantic config loading (unit)
2. `TestPIIRedactorUnit` — email, VIN, phone, SSN redaction (unit)
3. `TestRedactPIISkill` — `FunctionTool` adapter contract (unit)
4. `TestPIIEvalDataset` — dataset-driven parametrized eval (unit)
5. `TestAgentIntegration` — live API smoke tests (integration, skipped without key)

#### [NEW] `tests/evaluation/datasets/pii_redaction.jsonl`
5 evaluation cases: email, VIN, phone, SSN, and clean text.

#### [NEW] `tests/evaluation/datasets/telemetry_valid.jsonl`
3 cases: valid telemetry, dropout + low density, inconsistent velocity.

#### [NEW] `tests/evaluation/golden_dataset.json`
Array of structured golden dataset tasks for evaluating the orchestration agent trajectory, specifically tracking PII leakage. Contains the `forbidden_tokens` schema for strict verification.

#### [NEW] `tests/evaluation/test_golden_dataset.py`
Evaluation engine checking `golden_dataset.json` by invoking the `Session` live with `gemini-1.5-pro`. Audits output tokens and expected trajectory (enforces `clean_pii`).

#### [NEW] `tests/evaluation/datasets/labels_valid.jsonl`
4 cases: valid labels, category mismatch, missing labels, negative dimensions.

### Component: Knowledge Assets Extended (`assets/`) — Phase 9

#### [NEW] `assets/rules.txt`
Operational safety rules document structured as a formal regulatory specification.
Two active rules:
- **AV-REG-101** (Intersection Safety — Velocity Thresholds): Three zone-type tables
  (uncontrolled, controlled, school/pedestrian) with nominal and adverse condition limits.
  Defines three breach levels (WARN/ALERT/OVERRIDE) and a validation agent issue code spec
  (`AV-REG-101-BREACH`) with required field list.
- **AV-REG-102** (Sensor Obstruction Integrity Rules): Per-sensor Minimum Operational
  Threshold (MOT) table for LiDAR, cameras, RADAR, IMU, GNSS. Three obstruction levels
  (MINOR/MODERATE/SEVERE) with actions. Wet-road camera reflection protocol with
  confidence penalty rules. Multi-sensor fault escalation to MRC manoeuvre. Explicit
  interaction clause linking AV-REG-102 status to AV-REG-101 adverse condition mode.

#### [NEW] `assets/fleet_history.txt`
Long-context memory profile for AV-FLEET-402. Designed to be loaded as grounding context
for validation agents processing Zone 7 telemetry. Key contents:
- Full software stack state: `v4.2.1-beta` on core autonomy + perception (only unit in Zone 7)
- Active bug `BUG-CAM-402-WET-007`: camera reflection false positives on wet roads, introduced
  by the beta patch's normalisation layer change; phantom objects at confidence 0.62–0.74;
  safety-critical overlap with AV-REG-101 emergency deceleration threshold
- Validation agent disambiguation rules: apply 1.5× confidence penalty, tag SUSPECT_PHANTOM,
  do not raise AV-REG-102 alerts on phantom objects alone, always cross-validate with LiDAR
- Three-incident history with root causes and statuses
- Five-unit peer fleet comparison with software versions and bug status

#### [NEW] `assets/guardrails.txt`
Mandatory output safety constraints for the AV Validation Orchestrator. Four sections:
- **GR-TOK** (Token Audit, CRITICAL): Budget enforcement (2,048/8,192 token limits),
  JSON structural verification with two-attempt repair, repetition/padding detection
- **GR-LEAK** (Text Leakage, CRITICAL): System prompt leakage detection with sentinel phrases,
  PII re-exposure prevention via session-scoped registry, credential/secret pattern scanning
  (API keys, bearer tokens, private keys), internal infra reference suppression
- **GR-TONE** (Tone Normalisation, STANDARD): Emotional hyperbole stripping with prohibited
  phrase dictionary and neutral replacements, certainty calibration (over/under-confidence
  correction), corporate passive-voice and third-person enforcement, speculation prohibition
- **Enforcement Summary**: 11 guardrail IDs with class (CRITICAL/STANDARD) and failure actions

---

### Component: Enterprise PII Cleaner & Log Simulator (`src/skills/pii_redactor/`) — Phase 10

#### [NEW] `src/skills/pii_redactor/skill.md`
Tool manifest for `enterprise_av_security_pii_cleaner`. Declares:
- Tool name, version, implementation path, author, status, classification
- Strict JSON input schema (`$schema` draft-07): single required field `raw_log_text`
  (type: string, minLength: 1, maxLength: 65,536, additionalProperties: false)
- Full JSON output schema: `redacted_text`, `pii_found`, `redaction_summary` (per-category counts),
  `original_char_count`, `redacted_char_count`
- Regex pattern reference for all 3 PII categories with family descriptions
- CLI usage example with expected redacted output and summary
- Security notes: deterministic-only (no model inference), defence-in-depth positioning
- Integration pipeline diagram showing tool order in the full sanitisation chain

#### [NEW] `src/skills/pii_redactor/enterprise_av_security_pii_cleaner.py`
Deterministic, regex-driven PII cleaner. Architecture:
- `EnterpriseAVSecurityPIICleaner` class — stateful per-call, singleton at module level
- **3-pass execution order** (ordered to prevent pattern interference):
  - Pass 1 GPS: labelled (`lat/lon:`), keyword-prefixed (`GPS:/pos:/coord:`), bare decimal (≥4 dp)
  - Pass 2 Plates: keyword-anchored (`plate:/unit:/reg:/fleet id:`) + standalone format regex
  - Pass 3 Names: prefix-anchored (`Safety Driver:/SD/Operator:/Engineer:/Technician:` + optional title)
- Typed placeholders: `[DRIVER_REDACTED]`, `[PLATE_REDACTED]`, `[GPS_REDACTED]`
- `CleanerResult` dataclass: per-category counts, `pii_found`, `total_redactions`, `redaction_details`
- `clean_pii(raw_log_text)` — ADK `FunctionTool` adapter, plain `dict` return
- Module-level `_cleaner` singleton (thread-safe — regex ops are read-only)
- `if __name__ == "__main__"` CLI quick-test with realistic sample log

#### [NEW] `src/skills/pii_redactor/data_simulator.py`
Gemini 1.5 Flash synthetic log generator:
- `AVDisengagementLogSimulator` class — configurable temperature/token budget
- Prompt engineering: names all 3 PII types explicitly with formatting instructions
  (use different notation styles; embed naturally in messy prose; add typos/abbreviations)
- 12 randomised scenario seeds (pedestrian, wet road, construction zone, emergency vehicle, etc.)
- 20-name diverse driver pool; 10-plate pool (US/EU formats); 5 SF Bay Area GPS regions
- `generate(seed=)` returns `{log_text, metadata.injected_pii, generated_at, model}`
- `metadata.injected_pii` = ground truth record (driver name, both plates, both GPS coords)
  enabling automated PII recall evaluation against the cleaner
- `generate_batch(count=, seed=)` for bulk dataset generation (max 50 per call)
- CLI: `--count`, `--seed`, `--save` (JSONL to `tests/evaluation/datasets/`),
  `--temperature`, `--print-metadata`
- Graceful `ImportError` guard for environments without `google-generativeai`

---

---

### Component: Runtime Framework & UI Dashboard (`src/agent/`) — Phase 11

#### [NEW] `src/agent/app.py`
Entry point for the interactive validation dashboard. Combines the ADK 2.0 multi-agent backend
with a feature-rich three-tab Gradio frontend GUI.
- **Tab 1: Synthetic Data Generation Engine**
  - Features a large display text box showing generated raw log strings.
  - Action button: 'Generate Synthetic AV Log Data'.
  - Connects to the simulator skill module (`AVDisengagementLogSimulator`) backed by `gemini-1.5-flash`.
- **Tab 2: Secure Validation Audit Portal**
  - Input text field for pasting raw logs.
  - Action button: 'Run Safe Validation Audit'.
  - Executes the `enterprise_av_security_pii_cleaner` tool to mask driver fields before model processing.
  - Intermediate textbox showing the 'Purified Outbound Prompt Context'.
  - Markdown window presenting the final audited corporate compliance report via `av_compliance_agent` (backed by `gemini-1.5-pro`).
- **Tab 3: Automated Performance Evaluation**
  - Action button: 'Execute Trajectory & PII Leak Audit Suite'.
  - Programmatically runs test cases against validation rules.
  - Renders raw metrics and passing state data clearly on screen.
- **Architecture**:
  - Modular singleton initialization for agents and models.
  - Strict stage separation in Tab 2 ensures no raw text reaches the LLM.
  - Custom dark enterprise UI aesthetic for the Gradio frontend.

---

### Component: Core Agent Tools (`src/skills/validation/`) — Phase 12

#### [NEW] `src/skills/validation/telemetry_validator.py`
Replaces the `validate_telemetry` placeholder.
- Deterministic checks against `AV-REG-102` thresholds (e.g., LiDAR `< 10,000` points per sweep).
- Detects sensor dropouts and timestamp gaps.
- Flags inconsistent velocity deltas.

#### [NEW] `src/skills/validation/label_validator.py`
Replaces the `validate_labels` placeholder.
- Verifies label dimension constraints (no negative sizes).
- Checks for missing annotation lists.
- Ensures classification consistency across frames for matching tracking IDs.

#### [NEW] `src/skills/validation/report_generator.py`
Replaces the `generate_report` placeholder.
- Aggregates issues from both telemetry and labels.
- Calculates severity summaries for incident reporting (CRITICAL vs HIGH).
- Formats validation findings cleanly to act as constraints for the LLM output.

#### [MODIFY] `src/agent/agent.py`
- Removed dummy tool implementations.
- Imported and injected real implementations from `src/skills/validation/` into `FunctionTool`.
- Embedded `rules.txt` and `guardrails.txt` into the orchestrator agent context at startup.
- Registered `retrieve_knowledge_tool` for runtime file access.

### Component: Core Skills (`src/skills/`) — Phases 13 & 15

#### [NEW] `src/skills/knowledge_retrieval.py`
- Simple safe file-reader tool exposing `assets/` to the agent.

#### [NEW] `src/skills/kaggle/pipeline.py`
- Implemented `KagglePipeline` encapsulating API calls for downloading competition datasets and formatting JSONL submissions from validation reports.

### Component: Infrastructure (`.github/` & `.pre-commit-config.yaml`) — Phase 14
- Configured `.github/workflows/ci.yml` for automated pytest on push/PR.
- Setup Dependabot in `.github/dependabot.yml` for weekly pip updates.
- Configured `.pre-commit-config.yaml` to run `ruff` and `mypy` locally.

---

### Component: Docs (`docs/implementation/`)

#### [NEW] `docs/implementation/implementation_plan.md`
This file. Documents the full design intent and file-level change rationale.

#### [NEW] `docs/implementation/tasks.md`
Chronological task log tracking completion status of every work item.

#### [NEW] `docs/implementation/walkthrough.md`
Narrative walkthrough of the scaffolded project: structure, design decisions,
key commands, and next steps for extending the agent.

---

## Verification Plan

### Automated Tests
- `pytest tests/evaluation/test_validation_tools.py -v -m "unit"` tests the deterministic tool logic against ground truth expected outcomes in `telemetry_valid.jsonl` and `labels_valid.jsonl`.
```bash
pytest tests/evaluation/ -v -m "unit"           # Fast unit suite
pytest tests/evaluation/ -v -m "integration"    # Live API suite
```

### Manual Verification
- `adk web src/agent/` launches the ADK Dev UI without errors
- `python src/skills/pii_redactor/enterprise_av_security_pii_cleaner.py` redacts all 3 PII types from sample log
- `python -m src.skills.pii_redactor.data_simulator` generates a log with driver name, plate, and GPS embedded
- `python src/agent/app.py` successfully launches the Gradio 3-tab dashboard.
- `.env` is NOT present in `git log --name-only`
- `pytest tests/evaluation/test_validation_tools.py` successfully passes 7 cases for the implemented validation tools.
- `pytest tests/evaluation/test_golden_dataset.py` successfully injects `golden_dataset.json` and evaluates zero PII leakage.
- `git push origin main` succeeds and all files appear on GitHub

---

### Component: Map & Weather API Integrations
- Added Geocoding (Road Name, County)
- Added Roads API (Speed Limits)
- Added Open-Meteo API (Weather)
- Added Street View interactive iframe

---

*Last updated: 2026-06-20 | Phase: Phase 17 — Integrate Enhanced Map & Weather APIs*
