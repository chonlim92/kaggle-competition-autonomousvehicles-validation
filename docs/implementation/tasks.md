# Tasks — AV Validation Agent

> Chronological task log. Updated after each implementation phase.
> Status: `[x]` done · `[/]` in progress · `[ ]` not started

---

## Phase 1 — Repository Initialization ✅

- [x] Clone remote repo `https://github.com/chonlim92/kaggle-competition-autonomousvehicles-validation.git`
  - Cloned into `kaggle-competition-autonomousvehicles-validation/` subdirectory
  - Repository was empty (no initial commit)
- [x] Verify clone succeeded and branch `main` is tracked

---

## Phase 2 — Root Scaffolding ✅

- [x] Create `.env` with `GEMINI_API_KEY` and `GOOGLE_GENAI_USE_ENTERPRISE=FALSE`
- [x] Create `.env.example` (committed template for team onboarding)
- [x] Create `.gitignore`
  - Covers `.env`, Python build artefacts, virtual environments, IDE configs, ADK sessions
- [x] Create `README.md`
  - Quickstart, directory tree, env var reference, architecture overview
- [x] Create `pyproject.toml`
  - `google-adk>=2.0.0`, `presidio-analyzer`, `presidio-anonymizer`, `pydantic>=2.7.0`
  - Dev extras: `pytest`, `ruff`, `mypy`, `pre-commit`

---

## Phase 3 — Core Orchestrator Agent (`src/agent/`) ✅

- [x] Create `src/agent/__init__.py` — exports `root_agent`
- [x] Create `src/agent/config.py`
  - Pydantic `AgentConfig` model, frozen, `@lru_cache` singleton
  - Reads all settings from `.env` via `python-dotenv`
- [x] Create `src/agent/prompts.py`
  - `ORCHESTRATOR_SYSTEM_PROMPT` — AV expert persona, JSON output format
  - `PII_REDACTOR_TASK_PROMPT` — sub-task prompt
- [x] Create `src/agent/agent.py`
  - `root_agent` as ADK `LlmAgent` with `gemini-2.0-flash`
  - Registered tools: `redact_pii`, `validate_telemetry`, `validate_labels`, `generate_report`

---

## Phase 4 — PII Redactor Skill (`src/skills/pii_redactor/`) ✅

- [x] Create `src/skills/__init__.py`
- [x] Create `src/skills/pii_redactor/__init__.py` — exports `redact_pii`
- [x] Create `src/skills/pii_redactor/redactor.py`
  - `PIIRedactor` class with Presidio primary engine + regex fallback
  - Custom `PatternRecognizer` for VINs (17-char) and licence plates (EU/US)
  - Three redaction modes: `mask`, `redact`, `tokenize`
  - `RedactionResult` dataclass
- [x] Create `src/skills/pii_redactor/skill.py`
  - `redact_pii()` — ADK `FunctionTool` adapter with full docstring

---

## Phase 5 — Knowledge Assets (`assets/`) ✅

- [x] Create `assets/README.md` — structure and usage guide
- [x] Create `assets/knowledge/av_domain_glossary.md`
  - AV terminology, sensor modalities, annotation standards
  - Validation rules by severity (CRITICAL / HIGH / MEDIUM / LOW)
  - PII types in AV data, coordinate frames, Kaggle specifics

---

## Phase 6 — Evaluation Suite (`tests/evaluation/`) ✅

- [x] Create `tests/__init__.py`
- [x] Create `tests/evaluation/__init__.py`
- [x] Create `tests/evaluation/README.md` — run commands, format, metrics
- [x] Create `tests/evaluation/conftest.py`
  - Session-scoped fixtures: `agent_config`, `pii_redactor`, dataset loaders
  - Custom pytest markers: `unit`, `integration`, `slow`
- [x] Create `tests/evaluation/test_agent_eval.py`
  - `TestAgentConfig` — config validation (5 unit tests)
  - `TestPIIRedactorUnit` — email, VIN, phone, SSN, clean, flag, fields (7 unit tests)
  - `TestRedactPIISkill` — dict contract, keys, lengths (3 unit tests)
  - `TestPIIEvalDataset` — dataset-driven JSONL eval
  - `TestAgentIntegration` — live API smoke tests (2 integration tests)
- [x] Create `tests/evaluation/datasets/pii_redaction.jsonl` — 5 PII cases
- [x] Create `tests/evaluation/datasets/telemetry_valid.jsonl` — 3 telemetry cases
- [x] Create `tests/evaluation/datasets/labels_valid.jsonl` — 4 label cases

---

## Phase 7 — Git Commit & Push ✅

- [x] `git add -A` — stage all 22 files (`.env` correctly excluded)
- [x] `git commit` — conventional commit message documenting all changes
  - Commit: `757b73b` on branch `main`
  - 22 files changed, 1,377 insertions
- [x] `git push origin main` — push to `https://github.com/chonlim92/kaggle-competition-autonomousvehicles-validation`
  - Result: `* [new branch] main -> main` ✅

---

## Phase 8 — Docs Folder (`docs/implementation/`) ✅

- [x] Create `docs/implementation/implementation_plan.md`
- [x] Create `docs/implementation/tasks.md` (this file)
- [x] Create `docs/implementation/walkthrough.md`
- [ ] Commit and push `docs/implementation/` to remote

---

## Phase 9 — Knowledge Assets Population (`assets/`) ✅

- [x] Create `assets/rules.txt` — Driving Safety Protocol document
  - `RULE_ID: AV-REG-101` — Intersection velocity thresholds (3 zone tables: uncontrolled, controlled, school zones; nominal + adverse conditions; breach levels WARN/ALERT/OVERRIDE; validation agent issue code spec)
  - `RULE_ID: AV-REG-102` — Sensor obstruction integrity rules (5-sensor MOT table; 3 obstruction levels; wet-road camera reflection protocol; multi-sensor fault escalation; AV-REG-101 interaction clause)
- [x] Create `assets/fleet_history.txt` — Long-context fleet memory profile for AV-FLEET-402
  - Beta software patch `v4.2.1-beta` (PATCH-402-V421B) — isolated rollout, 1 unit only
  - Active bug `BUG-CAM-402-WET-007` — camera reflection false positives on wet roads (confidence 0.62–0.74); 1.5× confidence penalty rule
  - 3-incident operational history; peer fleet comparison table (5 units)
  - Validation agent disambiguation rules for wet-road phantom objects
- [x] Create `assets/guardrails.txt` — AI output safety constraints
  - Section 1 (GR-TOK): Token budget enforcement, JSON structure verification, repetition/padding detection
  - Section 2 (GR-LEAK): System prompt leakage, PII re-exposure, credential/secret detection, internal infra suppression
  - Section 3 (GR-TONE): Emotional hyperbole stripping (prohibited phrase dictionary + neutral replacements), certainty calibration, passive-voice compliance, speculation prohibition
  - Section 4: Enforcement summary table (11 guardrail IDs, CRITICAL vs STANDARD)
- [ ] Commit and push Phase 9 assets to remote

---

## Pending / Future Phases

### Phase 10 — Tool Implementation
- [ ] Implement `validate_telemetry` — sensor range checks, dropout detection, timestamp gap analysis (referencing AV-REG-102 MOT thresholds)
- [ ] Implement `validate_labels` — IOU checks, class distribution, category consistency
- [ ] Implement `generate_report` — severity aggregation, Kaggle JSONL report formatter (applying GR-TOK and GR-TONE guardrails)

### Phase 11 — RAG Knowledge Base
- [ ] Wire `assets/rules.txt`, `assets/fleet_history.txt`, `assets/guardrails.txt`, and `assets/knowledge/av_domain_glossary.md` into `google.adk.tools.retrieval` or equivalent
- [ ] Embed safety rules and guardrails into agent context at startup

### Phase 12 — CI/CD
- [ ] Add GitHub Actions workflow for `pytest -m "unit"` on every PR
- [ ] Add pre-commit hooks: `ruff`, `mypy`
- [ ] Add Dependabot for `pyproject.toml` dependency updates

### Phase 13 — Kaggle Integration
- [ ] Add Kaggle API client for dataset download (`kaggle competitions download`)
- [ ] Add data pipeline for ingesting AV scene files
- [ ] Add submission generator (`generate_report` → Kaggle JSONL format)

---

*Last updated: 2026-06-20 | Phase 9 complete*
