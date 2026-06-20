# Autonomous Vehicles Validation Agent

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
