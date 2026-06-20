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

## Pending / Future Phases

### Phase 9 — Tool Implementation
- [ ] Implement `validate_telemetry` — sensor range checks, dropout detection, timestamp gap analysis
- [ ] Implement `validate_labels` — IOU checks, class distribution, category consistency
- [ ] Implement `generate_report` — severity aggregation, Kaggle JSONL report formatter

### Phase 10 — RAG Knowledge Base
- [ ] Wire `assets/knowledge/` into `google.adk.tools.retrieval` or equivalent
- [ ] Embed glossary and rules into agent context at startup

### Phase 11 — CI/CD
- [ ] Add GitHub Actions workflow for `pytest -m "unit"` on every PR
- [ ] Add pre-commit hooks: `ruff`, `mypy`
- [ ] Add Dependabot for `pyproject.toml` dependency updates

### Phase 12 — Kaggle Integration
- [ ] Add Kaggle API client for dataset download (`kaggle competitions download`)
- [ ] Add data pipeline for ingesting AV scene files
- [ ] Add submission generator (`generate_report` → Kaggle JSONL format)

---

*Last updated: 2026-06-20 | Phase 8 complete*
