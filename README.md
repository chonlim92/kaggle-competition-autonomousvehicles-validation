# Autonomous Vehicles Validation Agent

Author: Chong Kiat Lim (associated by Google Antigravity)

> **Production-grade ADK 2.0 agent** for Kaggle's Autonomous Vehicles Validation competition.

## Project Structure

```
.
├── .env                        # 🔑 Local secrets (never committed)
├── .env.example                # Template for onboarding
├── pyproject.toml              # Dependency management (uv / pip)
├── README.md
│
├── src/
│   ├── agent/                  # 🧠 Core orchestrator agent
│   │   ├── __init__.py
│   │   ├── agent.py            # Root ADK Agent definition
│   │   ├── config.py           # Runtime configuration loader
│   │   └── prompts.py          # System prompts & persona
│   │
│   └── skills/                 # 🛠️  Custom ADK tool skills
│       └── pii_redactor/
│           ├── __init__.py
│           ├── skill.py        # PII redactor ADK Skill wrapper
│           └── redactor.py     # Core redaction logic
│
├── assets/                     # 📚 Localized text knowledge assets
│   ├── README.md
│   └── knowledge/
│       └── av_domain_glossary.md
│
└── tests/
    ├── __init__.py
    └── evaluation/             # 🧪 Agent evaluation suites
        ├── __init__.py
        ├── README.md
        ├── conftest.py
        ├── datasets/           # Eval datasets (JSONL)
        └── test_agent_eval.py
```

## Quickstart

```bash
# 1. Clone & enter project
git clone https://github.com/chonlim92/kaggle-competition-autonomousvehicles-validation.git
cd kaggle-competition-autonomousvehicles-validation

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Copy env template and fill in secrets
cp .env.example .env

# 5. Run the agent (ADK dev UI)
adk web src/agent/

# 6. Run evaluation suite
pytest tests/evaluation/ -v
```

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `GOOGLE_GENAI_USE_ENTERPRISE` | Use Vertex AI Enterprise endpoint |
| `APP_ENV` | Runtime environment (`development` / `production`) |
| `PII_REDACTION_MODE` | PII masking strategy (`mask` / `redact` / `tokenize`) |

## Architecture

- **Orchestrator** (`src/agent/agent.py`) — Root ADK 2.0 `Agent` with tool routing
- **PII Redactor Skill** (`src/skills/pii_redactor/`) — Strips personally identifiable information from vehicle telemetry data before LLM processing
- **Knowledge Assets** (`assets/knowledge/`) — Domain glossary, validation rules, grounding context
- **Evaluation** (`tests/evaluation/`) — ADK `EvalSet`-compatible test suites for accuracy, safety, and latency

## App Features (Gradio Dashboard)

The local Gradio frontend (`src/agent/app.py`) provides an interactive interface with three tabs:
1. **Synthetic Data Generation Engine**: Automatically generates realistic, messy AV disengagement logs embedded with randomized PII and coordinates using `gemini-1.5-flash`.
2. **Secure Validation Audit Portal**: Simulates the compliance auditing flow. It first scrubs any PII using deterministic regex (Defence-in-Depth), then passes the purified text to the `gemini-1.5-pro` orchestrator agent to produce a structured compliance and safety report.
3. **Automated Performance Evaluation**: Automatically runs the `adk eval` trajectory tests against the golden dataset to evaluate PII redaction accuracy and guardrail safety rule adherence locally.

## Tech Stack

| Component / Skill | Description |
|-------------------|-------------|
| **Google ADK 2.0** | Agent framework for orchestrating LLM tool calling and evaluation. |
| **Gradio** | Frontend web UI for interactive dashboard and visualizations. |
| **Folium** | Map rendering and interactive geographic data plotting. |
| **Pytest** | Automated unit and integration testing suite. |
| **Pre-commit** | Git hooks for enforcing code styling and formatting rules. |
| **Regex Sanitisation** | Custom deterministic regex engine for PII masking (names, plates, GPS). |
| **Gemini 1.5 Flash/Pro** | High-throughput data generation (Flash) and deep reasoning compliance (Pro). |
