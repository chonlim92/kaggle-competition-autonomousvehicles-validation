# Walkthrough — AV Validation Agent

> Narrative summary of every implementation phase. Updated after each change.

---

## Phase 1 — Repository Initialization

**Date**: 2026-06-20  
**Branch**: `main`

The remote GitHub repository `kaggle-competition-autonomousvehicles-validation` was empty.
We cloned it into a subdirectory of the workspace:

```
IntensiveVibeCodingCourseWithGoogle/
└── kaggle-competition-autonomousvehicles-validation/   ← cloned here
```

The workspace root already contained five course-day directories, so cloning into `.`
would have failed — the subdirectory approach was the correct call.

---

## Phase 2 — Root Scaffolding

**Files created**: `.env`, `.env.example`, `.gitignore`, `README.md`, `pyproject.toml`

### .env
Populated immediately with the provided credentials:
```
GEMINI_API_KEY="AIzaSyDB9IaT-9TDuaf_W5hOBX_5NkMeL0h8YVY"
GOOGLE_GENAI_USE_ENTERPRISE=FALSE
```
This file is listed in `.gitignore` and was **never staged or committed**, verified by
checking `git status` output (`.env` absent from the tracked files list).

### pyproject.toml
Chose `hatchling` as the build backend (lightweight, PEP 517 compliant, recommended
by the Python Packaging Authority). Key dependency decisions:
- `google-adk>=2.0.0` — minimum version pins to ADK 2.0 API surface
- `presidio-analyzer` + `presidio-anonymizer` — Microsoft's production PII framework;
  chosen over regex-only or cloud NLP APIs for its offline capability and extensibility
- `pydantic>=2.7.0` v2 API — frozen models, field validators, strong typing
- `structlog` — structured JSON logging preferred over stdlib `logging` for
  production observability pipelines

---

## Phase 3 — Core Orchestrator Agent

**Files created**: `src/agent/__init__.py`, `src/agent/config.py`, `src/agent/prompts.py`, `src/agent/agent.py`

### Architecture decision: single `root_agent`
The ADK 2.0 convention for `adk web <path>` and `adk run <path>` is to expose a module-level
`root_agent` variable. We placed this in `src/agent/agent.py` and re-exported it via
`src/agent/__init__.py` so the agent is addressable as both `src/agent/` (CLI) and
`src.agent` (import).

### Config singleton
`AgentConfig` is frozen (`model_config = {"frozen": True}`) to prevent accidental
mutation after startup. The `@lru_cache` on `get_config()` ensures `.env` is read
exactly once per process — important for test isolation where the config must be
consistent across the session.

### Prompts separation
`prompts.py` holds system prompts as module-level string constants rather than
embedding them inside `agent.py`. This makes prompt iteration a one-file change
that can be reviewed independently of agent wiring.

### Tool slots
Four `FunctionTool` wrappers are registered on `root_agent`. Two are fully implemented
(`redact_pii`), two are intentional placeholders with `TODO` comments:

```
root_agent
  ├── redact_pii          ✅ fully implemented
  ├── validate_telemetry  🔲 placeholder — extend with AV logic
  ├── validate_labels     🔲 placeholder — extend with AV logic
  └── generate_report     🔲 placeholder — extend with AV logic
```

The placeholder pattern is intentional: it establishes the tool interface contract
(function signature, docstring, return shape) so the LLM can already route to these
tools, and the implementation can be filled in without changing the agent definition.

---

## Phase 4 — PII Redactor Skill

**Files created**: `src/skills/__init__.py`, `src/skills/pii_redactor/__init__.py`,
`src/skills/pii_redactor/redactor.py`, `src/skills/pii_redactor/skill.py`

### Two-layer architecture
```
skill.py          ← ADK interface layer (FunctionTool adapter)
redactor.py       ← Core logic layer (PIIRedactor class)
```
This separation means the core logic can be tested without ADK, and the ADK adapter
can be swapped if the tool registration API changes.

### Presidio with graceful degradation
`presidio-analyzer` requires a spaCy NER model (`en_core_web_lg`, ~750 MB). In a
fresh environment the model may not be installed. The `try/except ImportError` block
falls back to regex-only redaction rather than crashing the agent at startup. This is
logged at `WARNING` level so it's visible but not fatal.

### Custom AV-domain recognizers
Two custom `PatternRecognizer` instances extend the default Presidio entity set:

| Recognizer | Pattern | Score |
|-----------|---------|-------|
| `VEHICLE_ID` | `[A-HJ-NPR-Z0-9]{17}` | 0.85 |
| `LICENSE_PLATE` | `[A-Z]{1,3}[-]?\d{1,4}[-]?[A-Z]{0,3}` | 0.60 |

VINs are high-confidence (rigid 17-char structure); licence plates are lower-confidence
(many false positives in technical strings).

### Three redaction modes
- **mask** (default) — replaces with `[REDACTED]` or configured placeholder
- **redact** — replaces with `<ENTITY_TYPE>` (e.g. `<EMAIL_ADDRESS>`)
- **tokenize** — SHA-256 hash (preserves uniqueness for analytics without exposing PII)

---

## Phase 5 — Knowledge Assets

**Files created**: `assets/README.md`, `assets/knowledge/av_domain_glossary.md`

The `av_domain_glossary.md` file serves as the primary grounding document for the agent.
It was populated with domain knowledge across seven sections:

1. Core AV terminology
2. Sensor modalities and their failure modes
3. 3D bounding box annotation standard (NuScenes-compatible)
4. 12 standard object categories
5. Validation rules by severity (4 CRITICAL, 4 HIGH, 3 MEDIUM, 2 LOW)
6. PII types specific to AV datasets (VIN, licence plate, GPS home address, etc.)
7. Kaggle competition metrics and submission format

This file is intended to be loaded as a RAG knowledge source in a future phase.

---

## Phase 6 — Evaluation Suite

**Files created**: `tests/__init__.py`, `tests/evaluation/__init__.py`,
`tests/evaluation/README.md`, `tests/evaluation/conftest.py`,
`tests/evaluation/test_agent_eval.py`,
`tests/evaluation/datasets/pii_redaction.jsonl`,
`tests/evaluation/datasets/telemetry_valid.jsonl`,
`tests/evaluation/datasets/labels_valid.jsonl`

### Test pyramid
```
Unit tests  (no API)  ← fast, always run
   ↓
Skill tests (no API)  ← test tool contracts
   ↓
Dataset-driven        ← JSONL parametrized
   ↓
Integration (live API) ← gated by CI secret
```

The `@pytest.mark.integration` + `autouse` skip fixture pattern means integration
tests are automatically skipped in environments without `GEMINI_API_KEY` — no manual
`-m "not integration"` flag needed for local development.

### JSONL dataset format
```json
{"id": "pii-001", "input": "...", "pii_strings": ["..."], "tags": [...]}
```
`pii_strings` lists the exact strings that must NOT appear in `redacted_text` after
processing — a precision-focused eval that avoids requiring exact output matching.

---

## Phase 7 — Initial Git Commit & Push

**Commit**: `757b73b`  
**Files**: 22 files, 1,377 insertions  
**Remote**: `https://github.com/chonlim92/kaggle-competition-autonomousvehicles-validation`

The commit message follows the Conventional Commits specification with a detailed
body documenting all components. The `.env` file was confirmed absent from the
staged set before committing.

Push result:
```
* [new branch]      main -> main
```

---

## Phase 8 — Docs Folder

**Date**: 2026-06-20  
**Files created**: `docs/implementation/implementation_plan.md`,
`docs/implementation/tasks.md`, `docs/implementation/walkthrough.md` (this file)

Created a permanent `docs/implementation/` directory to house living documentation
that travels with the code. All three files are populated from the actual work
performed in phases 1–7, not from templates.

**Update policy**: After each implementation phase, all three files in
`docs/implementation/` are updated before the git commit, so the documentation
history stays in sync with code history.

---

## Phase 9 — Knowledge Assets Population

**Date**: 2026-06-20
**Files created**: `assets/rules.txt`, `assets/fleet_history.txt`, `assets/guardrails.txt`

### rules.txt — Design decisions

`rules.txt` is authored as a formal regulatory document with version control, an authority
header, and structured rule blocks. Each rule uses a consistent schema:

```
RULE_ID / Category / Severity / Status / Applies To
  → Purpose, Definitions, Thresholds (tables), Breach Conditions,
    Compliance Actions, Validation Agent Rule, Exceptions
```

**AV-REG-101** defines velocity thresholds across three intersection classes and two road
condition states. The "Validation Agent Rule" sub-section is key: it tells the agent
exactly what issue code to emit, what severity to assign, and what fields are required in
the output. This makes the rule machine-actionable, not just human-readable.

**AV-REG-102** introduces the critical link between sensor health and velocity compliance:
when a Level 2 or Level 3 sensor fault is active, the vehicle automatically enters
"Adverse Conditions" for AV-REG-101 purposes. This cross-rule interaction means the agent
must evaluate both rules together, not independently.

The wet-road camera reflection protocol in AV-REG-102 was written to directly address
BUG-CAM-402-WET-007 documented in `fleet_history.txt` — the two files are intentionally
cross-referenced to create a coherent grounding context for the agent.

### fleet_history.txt — Design decisions

The file is structured as a **long-context memory profile** — a term deliberately chosen
because it signals to the agent that this is grounding context with higher precedence than
general training data. The preamble explicitly states this.

The bug entry for BUG-CAM-402-WET-007 is written at two levels:
1. **Human-readable narrative** — root cause, impact profile, reproduction conditions
2. **Machine-actionable agent rules** — numbered steps telling the agent exactly how to
   process AV-FLEET-402 wet-road data differently from other fleet units

This dual-level structure ensures the document serves both as an engineering reference and
as a reliable in-context grounding source for the LLM-based orchestrator.

The peer fleet comparison table is intentional: it gives the agent a clear baseline to
understand that AV-FLEET-402's wet-road anomalies are not fleet-wide, preventing
over-generalisation of the bug to other units.

### guardrails.txt — Design decisions

Guardrails are structured in two severity classes:
- **CRITICAL** — hard stops. Output is suppressed entirely on failure. Covers security
  (credential leakage, infra exposure), privacy (PII re-exposure), and structural integrity
  (malformed JSON, token budget overflow).
- **STANDARD** — corrective transforms. Output is modified and released. Covers tone,
  certainty calibration, and voice compliance.

The `GR-LEAK-001` exception clause is important: rule IDs (AV-REG-101, AV-REG-102) and
bug IDs (BUG-CAM-402-WET-007) are explicitly permitted in outputs when directly relevant
to a finding. Without this exception, the guardrail would suppress legitimate structured
references that the agent must include in compliance reports.

The prohibited phrase dictionary in `GR-TONE-001` includes explicit replacements, not just
a blocklist. This ensures the agent always has a compliant alternative available rather
than silently omitting content.

---


```
kaggle-competition-autonomousvehicles-validation/
├── .env                              ✅ (local only, not in git)
├── .env.example                      ✅
├── .gitignore                        ✅
├── README.md                         ✅
├── pyproject.toml                    ✅
│
├── docs/
│   └── implementation/
│       ├── implementation_plan.md    ✅
│       ├── tasks.md                  ✅
│       └── walkthrough.md            ✅ (this file)
│
├── src/
│   ├── agent/
│   │   ├── __init__.py               ✅
│   │   ├── agent.py                  ✅ (root_agent + 4 tools)
│   │   ├── config.py                 ✅ (Pydantic AgentConfig)
│   │   └── prompts.py                ✅ (AV orchestrator prompt)
│   └── skills/
│       └── pii_redactor/
│           ├── __init__.py           ✅
│           ├── redactor.py           ✅ (Presidio + regex fallback)
│           └── skill.py              ✅ (FunctionTool adapter)
│
├── assets/
│   ├── README.md                     ✅
│   ├── rules.txt                     ✅ NEW — AV-REG-101 + AV-REG-102
│   ├── fleet_history.txt             ✅ NEW — AV-FLEET-402 memory profile
│   ├── guardrails.txt                ✅ NEW — GR-TOK/LEAK/TONE constraints
│   └── knowledge/
│       └── av_domain_glossary.md     ✅
│
└── tests/
    └── evaluation/
        ├── README.md                 ✅
        ├── conftest.py               ✅ (session fixtures)
        ├── test_agent_eval.py        ✅ (4-layer test pyramid)
        └── datasets/
            ├── pii_redaction.jsonl   ✅ (5 cases)
            ├── telemetry_valid.jsonl ✅ (3 cases)
            └── labels_valid.jsonl    ✅ (4 cases)
```

---

## Phase 10 — Enterprise PII Cleaner & Log Simulator

**Date**: 2026-06-20  
**Files created**: `src/skills/pii_redactor/skill.md`, `src/skills/pii_redactor/enterprise_av_security_pii_cleaner.py`, `src/skills/pii_redactor/data_simulator.py`

### skill.md — Design decisions

The tool manifest follows the ADK skill documentation convention: it exists alongside the
Python implementation to make the tool self-documenting without needing to read source code.
Key design choices in the manifest:

- **`additionalProperties: false`** in the input schema — enforces strict contract, rejects any
  extra fields the LLM might hallucinate into the call
- **Dual output schema** — separate `redaction_summary` dict (per-category counts) and
  `redaction_details` list (per-entity metadata) gives downstream evaluation code two levels
  of granularity without over-inflating the primary output
- **`GR-LEAK-001` exception clause documented** — the manifest explicitly notes that rule IDs
  and bug IDs are permitted in outputs, preventing engineers from misapplying the guardrail

### enterprise_av_security_pii_cleaner.py — Design decisions

**3-pass order matters critically.** The order GPS → Plates → Names was chosen to prevent
pattern interference:

1. GPS first: decimal coordinate strings like `37.7749` could match partial plate patterns
   (e.g., `7749` looks like a 4-digit plate segment). Removing coordinates first eliminates
   this false-positive risk.
2. Plates second: plate tokens (e.g., `GBX-1042`) could be partially matched by the name
   suffix regex if a plate happened to start with an uppercase letter sequence. Removing
   plates before name matching prevents this.
3. Names last: name patterns are the most context-dependent and least likely to create
   interference with already-redacted placeholders.

**Typed placeholders over generic `[REDACTED]`**: Using `[DRIVER_REDACTED]`, `[PLATE_REDACTED]`,
and `[GPS_REDACTED]` means downstream evaluation code can verify which *category* of PII was
found without re-running the cleaner. It also makes it obvious to a human reviewer what was
redacted and where, which is important for auditability (see `guardrails.txt` GR-LEAK-002).

**Singleton `_cleaner`**: The `EnterpriseAVSecurityPIICleaner` instance is created at module
load time. Regex patterns are compiled once at class definition (module level), making repeated
calls to `clean_pii()` very fast — no per-call compilation overhead.

### data_simulator.py — Design decisions

**Ground truth metadata as first-class output**: Every simulated log includes
`metadata.injected_pii` containing the exact driver name, plate values, and GPS coordinates
that were injected. This transforms the simulator from a simple data generator into an
**evaluation dataset factory** — you can immediately compute PII recall by comparing
`metadata.injected_pii` against the cleaner's `redaction_details`.

**High temperature (0.95 default)**: AV logs are inherently varied in style and vocabulary.
High temperature ensures the simulator doesn't converge on a single log template, producing
the realistic diversity needed for robust evaluation.

**Prompt structure — explicit vs. implicit PII injection**: The prompt names the exact PII
values to embed (driver name, plate 1, plate 2, GPS 1, GPS 2) and requires different notation
styles for each GPS pair. This is intentional: the cleaner must handle notation variety, so
the simulator must produce it. The instruction to use different prefix formats (`GPS:`, `lat/lon:`,
bare decimal) maps directly to the three GPS regex patterns in the cleaner.

**`--save` flag auto-JSONL to eval datasets**: Generated logs land directly in
`tests/evaluation/datasets/` with an ISO timestamp filename. This creates a feedback loop:
generate → clean → evaluate → improve regex → repeat.

---

## Current State (Phase 10)

```
src/skills/pii_redactor/
  ├── __init__.py                           ✅
  ├── skill.md                              ✅ NEW — tool manifest + JSON schema
  ├── enterprise_av_security_pii_cleaner.py ✅ NEW — 3-pass regex engine
  ├── data_simulator.py                     ✅ NEW — Gemini 1.5 Flash log generator
  ├── redactor.py                           ✅ (Presidio engine, secondary sweep)
  └── skill.py                              ✅ (ADK FunctionTool for Presidio cleaner)
```

## Next Steps

| Phase | Task | Priority |
|-------|------|----------|
| 11 | Implement `validate_telemetry` — apply AV-REG-102 MOT thresholds, detect dropout | 🔴 High |
| 11 | Implement `validate_labels` — IOU, class consistency, missing labels | 🔴 High |
| 11 | Implement `generate_report` — apply GR-TOK token budget, GR-TONE normalisation | 🔴 High |
| 12 | Wire all four `assets/` files into ADK retrieval tool for RAG | 🟡 Medium |
| 13 | GitHub Actions CI for `pytest -m "unit"` on PRs | 🟡 Medium |
| 14 | Kaggle API integration for dataset download + submission | 🟢 Low |

---

*Last updated: 2026-06-20 | Phase 10 complete — enterprise PII cleaner and log simulator built*
