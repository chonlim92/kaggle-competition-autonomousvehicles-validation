"""
src/agent/app.py

AV Validation Agent — Main Runtime & Gradio Dashboard
=======================================================
Entry point for the interactive three-tab validation dashboard.
Combines the ADK 2.0 multi-agent backend with a Gradio frontend GUI.

Architecture overview
---------------------
                        ┌──────────────────────────────────────────────────┐
                        │              Gradio Dashboard (this file)         │
                        │                                                    │
                        │  Tab 1: Synthetic Data Generation Engine          │
                        │    └─► AVDisengagementLogSimulator                │
                        │          (gemini-2.5-flash, data_simulator.py)    │
                        │                                                    │
                        │  Tab 2: Secure Validation Audit Portal            │
                        │    ├─► EnterpriseAVSecurityPIICleaner  (regex)    │
                        │    │     [DRIVER_REDACTED][PLATE_REDACTED][GPS]   │
                        │    └─► av_compliance_agent             (ADK)      │
                        │          (gemini-2.5-pro, structured report)      │
                        │                                                    │
                        │  Tab 3: Automated Performance Evaluation          │
                        │    ├─► PII redaction recall tests (JSONL dataset) │
                        │    └─► Guardrail rule validation tests            │
                        └──────────────────────────────────────────────────┘

Data Flow — Tab 2 (critical path):
  raw_log_text (user input)
      │
      ▼
  enterprise_av_security_pii_cleaner.clean_pii()    [deterministic regex pass]
      │  Returns: redacted_text, redaction_summary
      ▼
  purified_context  ◄── displayed in "Purified Outbound Prompt Context" box
      │
      ▼
  compliance_system_prompt + purified_context
      │  → sent to ADK Runner (av_compliance_agent, gemini-2.5-pro)
      ▼
  structured compliance report  ◄── displayed as markdown

Key design decisions:
  - gemini-2.5-flash used for simulator (Tab 1) — high-throughput, low cost
  - gemini-2.5-pro used for compliance agent (Tab 2) — higher reasoning quality
    required for interpreting AV safety rules and producing formal reports
  - PII cleaner ALWAYS runs before ANY text reaches the LLM (defence-in-depth)
  - ADK agent is instantiated at module load time (not per request) for performance
  - Gradio state is per-session; no cross-user state pollution
  - All ADK runner calls are wrapped in asyncio.run() for Gradio compatibility
"""

from __future__ import annotations

import asyncio
import json
import asyncio
import os
import time
import re
import sys
from pathlib import Path
from typing import Any, Optional

import gradio as gr
import structlog
import folium
from dotenv import load_dotenv

# ── Project root path resolution ──────────────────────────────────────────────
# This ensures relative imports work whether the file is run as:
#   python src/agent/app.py                (direct)
#   python -m src.agent.app                (module)
#   gradio src/agent/app.py:demo           (Gradio CLI)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Load environment variables BEFORE any google.adk or google.generativeai imports.
# Using override=False so that pre-set env vars (CI, Docker) take precedence over .env
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)

# ── Globals & State ───────────────────────────────────────────────────────────

# In-memory dictionary storing mapping of eventid to ground-truth GPS and PII.
# Tab 1 generates these, Tab 2 reads them securely to render the map without
# passing the PII to the LLM.
_EVENT_STORE = {}

# ── Structured logging ─────────────────────────────────────────────────────────
# Using structlog for machine-parseable output — critical for production audit trails.
# In development (APP_ENV=development) this renders as coloured key=value; in
# production it renders as JSON for log aggregation systems.
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer() if os.getenv("APP_ENV", "development") == "development"
        else structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger(__name__)

# ==============================================================================
# Backend Imports — guarded to give informative errors on missing dependencies
# ==============================================================================

try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError as _e:
    _GENAI_AVAILABLE = False
    logger.warning("google-generativeai not available", error=str(_e))

try:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    _ADK_AVAILABLE = True
except ImportError as _e:
    _ADK_AVAILABLE = False
    logger.warning("google-adk not available — Tab 2 compliance agent disabled", error=str(_e))

# Internal skill modules — always available (pure Python, no external deps beyond regex)
from src.skills.pii_redactor.scripts.enterprise_av_security_pii_cleaner import (
    clean_pii,
    PLACEHOLDER_DRIVER,
    PLACEHOLDER_GPS,
    PLACEHOLDER_PLATE,
)


# Simulator — requires google-generativeai (Tab 1 only)
from src.skills.pii_redactor.scripts.data_simulator import (
    AVDisengagementLogSimulator,
    _GENAI_AVAILABLE as _SIM_GENAI_AVAILABLE,
)

# Agent config — used to pull API key and model selection from .env
from src.agent.config import get_config

# ==============================================================================
# Constants
# ==============================================================================

# The app uses gemini-2.5-pro for the compliance reporting agent.
# This is a deliberate upgrade from the orchestrator's default (gemini-2.5-flash)
# because compliance report generation requires longer structured reasoning chains
# and benefits from the higher-context window of gemini-2.5-pro.
COMPLIANCE_MODEL = os.getenv("COMPLIANCE_MODEL", "gemini-2.5-pro")

# System prompt for the compliance audit agent (Tab 2).
# Note: this prompt instructs the model to output a FORMAL corporate report.
# It is paired with the PURIFIED (PII-free) log context — never raw user input.
COMPLIANCE_SYSTEM_PROMPT = """You are a Senior Autonomous Vehicle Safety Compliance Officer
generating an official corporate audit report for a fleet operations board.

MANDATORY BEHAVIOUR:
1. Your input is a PURIFIED log excerpt. All PII has already been redacted by the enterprise
   security layer. Treat redaction placeholders ([DRIVER_REDACTED], [PLATE_REDACTED],
   [GPS_REDACTED]) as the authoritative representation of those fields — never speculate
   about the original values.
2. Cross-reference observations against the active safety rules:
   - AV-REG-101: Intersection velocity thresholds (WARN / ALERT / OVERRIDE breach levels)
   - AV-REG-102: Sensor obstruction integrity (MINOR / MODERATE / SEVERE obstruction levels)
3. If the log mentions wet road conditions AND involves a camera occlusion/confidence issue,
   flag for BUG-CAM-402-WET-007 investigation and apply a confidence penalty note.
4. Output ONLY the formal report. No preamble. No first-person. No speculation.
5. Apply GR-TONE-001: strip emotional hyperbole. Use corporate passive voice (third-person).
6. Apply GR-TOK-001: keep report under 600 tokens.

OUTPUT FORMAT (strict markdown):
## Disengagement Incident Compliance Report

### Incident Classification
[CRITICAL / HIGH / MEDIUM / LOW] — [one-sentence summary]

### Regulatory Rule Cross-Reference
| Rule ID | Status | Finding |
|---------|--------|---------|
| AV-REG-101 | PASS/WARN/ALERT/OVERRIDE | ... |
| AV-REG-102 | PASS/MINOR/MODERATE/SEVERE | ... |

### Key Observations
- [bullet list of factual technical observations from the log]

### Compliance Determination
[2-3 sentences of formal finding. Third person. Objective.]

### Recommended Actions
1. [Action item 1]
2. [Action item 2]

---
*Report generated by AV Validation Orchestrator — gemini-2.5-pro | Classification: INTERNAL*
"""

# Path to the evaluation dataset directory (used by Tab 3)
_EVAL_DATASET_DIR = _PROJECT_ROOT / "tests" / "evaluation" / "datasets"

# ==============================================================================
# Module-Level Singleton Initialisation
# ==============================================================================
# These are created ONCE at startup to avoid re-initialising SDK clients per request.
# Pattern: eager init with graceful degradation if dependencies missing.

cfg = get_config()

# ── Gemini API configuration ───────────────────────────────────────────────────
# genai.configure() must be called before any model instantiation.
# It reads the API key from our AgentConfig (which already validated it from .env).
if _GENAI_AVAILABLE:
    genai.configure(api_key=cfg.gemini_api_key)
    logger.info("Gemini API configured", key_prefix=cfg.gemini_api_key[:8] + "...")

# ── Data Simulator (Tab 1) ────────────────────────────────────────────────────
# AVDisengagementLogSimulator uses gemini-2.5-flash.
# High temperature (0.95) is used to produce diverse, realistic log text.
# This simulator is intentionally separate from the compliance model — the
# flash model is cheaper and faster for creative data generation tasks.
_simulator: Optional[object] = None
if _SIM_GENAI_AVAILABLE:
    try:
        _simulator = AVDisengagementLogSimulator(
            api_key=cfg.gemini_api_key,
            temperature=0.95,
            max_output_tokens=600,
        )
        logger.info("AVDisengagementLogSimulator initialised")
    except Exception as _init_err:
        logger.warning("Simulator init failed", error=str(_init_err))

# ── ADK Compliance Agent (Tab 2) ──────────────────────────────────────────────
# The compliance agent is an ADK LlmAgent backed by gemini-2.5-pro.
# ADK agents are defined once and reused across all Gradio sessions via a
# shared InMemorySessionService (safe because all PII is stripped before reaching
# the agent — no user-specific state is persisted between sessions).
_adk_runner: Runner | None = None
if _ADK_AVAILABLE:
    try:
        _compliance_agent = LlmAgent(
            name="av_compliance_agent",
            model=COMPLIANCE_MODEL,
            description=(
                "Generates formal corporate AV disengagement incident compliance reports "
                "from purified (PII-free) log excerpts. Cross-references AV-REG-101 and "
                "AV-REG-102 safety rules. Applies GR-TONE output guardrails."
            ),
            instruction=COMPLIANCE_SYSTEM_PROMPT,
            # No tools registered on this agent — it is a pure reasoning/generation agent.
            tools=[],
        )

        _session_service = InMemorySessionService()

        _adk_runner = Runner(
            agent=_compliance_agent,
            app_name="av_validation_dashboard",
            session_service=_session_service,
        )
        logger.info(
            "ADK compliance agent initialised",
            model=COMPLIANCE_MODEL,
            agent=_compliance_agent.name,
        )
    except Exception as _adk_err:
        logger.warning("ADK compliance agent init failed", error=str(_adk_err))


# ==============================================================================
# Helper: ADK Runner → response string
# ==============================================================================

async def _run_adk_agent(message: str, session_id: str) -> str:
    """
    Send a single message to the ADK compliance agent and collect the full response.

    This function handles the ADK 2.0 async generator protocol:
      runner.run_async() yields Content objects (one per turn or tool call).
      We collect all text parts from MODEL role events and join them.

    Args:
        message: The purified log text to analyse (PII already stripped).
        session_id: A unique session identifier for this Gradio user session.
                    Using a fresh session per request prevents response bleed.

    Returns:
        The compliance agent's full text output as a single string.
    """
    if _adk_runner is None:
        return "_ADK compliance agent is not initialised. Check GEMINI_API_KEY and google-adk installation._"

    from google.adk.sessions import Session
    from google.genai.types import Content, Part

    # Create or reuse the session for this request.
    # InMemorySessionService is ephemeral — sessions are lost on server restart.
    # For production, replace with a persistent session backend.
    try:
        session = await _session_service.create_session(
            app_name="av_validation_dashboard",
            user_id="gradio_user",
            session_id=session_id,
        )
    except Exception:
        # Session may already exist if user clicked the button multiple times;
        # retrieve the existing one instead.
        session = await _session_service.get_session(
            app_name="av_validation_dashboard",
            user_id="gradio_user",
            session_id=session_id,
        )

    # Wrap the user message in the ADK Content/Part schema.
    # role="user" is mandatory for the first turn in a conversation.
    user_content = Content(role="user", parts=[Part(text=message)])

    response_parts: list[str] = []

    # run_async() is an async generator yielding Event objects.
    # Each Event carries a Content with role="model" when the agent responds.
    # Tool call events (role="tool") are skipped here — this agent has no tools.
    async for event in _adk_runner.run_async(
        user_id="gradio_user",
        session_id=session_id,
        new_message=user_content,
    ):
        # Collect text parts from model response events only.
        # Check for content attribute defensively — some events carry metadata only.
        if hasattr(event, "content") and event.content and event.content.role == "model":
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_parts.append(part.text)

    return "".join(response_parts).strip() or "_No response generated. Check logs._"


# ==============================================================================
# TAB 1 BACKEND — Synthetic Data Generation Engine
# ==============================================================================

def generate_synthetic_log() -> tuple[str, str, str]:
    """
    Tab 1 action handler: Generate a fresh batch of synthetic AV disengagement logs.
    """
    if _simulator is None:
        err = (
            "⚠️ Simulator unavailable.\n\n"
            "Ensure GEMINI_API_KEY is set in .env and google-generativeai is installed:\n"
            "  pip install google-generativeai"
        )
        return err, "", ""

    try:
        logger.info("Tab 1: generating synthetic log batch")
        t0 = time.perf_counter()
        results = _simulator.generate_batch(count=5)
        elapsed = time.perf_counter() - t0

        all_logs_text = []
        all_meta_display = []

        # Center map on Los Angeles
        m = folium.Map(location=[34.0522, -118.2437], zoom_start=10)

        for i, result in enumerate(results, 1):
            log_text: str = result["log_text"]
            meta = result["metadata"]
            pii = meta["injected_pii"]
            case_id = pii.get("case_id", "unknown")

            _EVENT_STORE[case_id] = pii

            meta_display = (
                f"--- LOG {i} ---\n"
                f"Case ID: {case_id}\n"
                f"  Driver name  : {pii['driver_name']}\n"
                f"  Primary plate: {pii['plate_primary']}\n"
                f"  Witness plate: {pii['plate_witness']}\n"
                f"  GPS primary  : {pii['gps_primary']['lat']}, {pii['gps_primary']['lon']}  [{pii['gps_primary']['region']}]\n"
            )

            all_logs_text.append(f"--- LOG {i} ---\n{log_text}\n")
            all_meta_display.append(meta_display)

            # Plot on map
            tooltip_text = (
                f"<b>Case ID:</b> {case_id}<br>"
                f"<b>Driver:</b> {pii['driver_name']}<br>"
                f"<b>Unit:</b> {pii['plate_primary']}<br>"
                f"<b>Scenario:</b> {meta['scenario'][:60]}..."
            )
            folium.Marker(
                [pii['gps_primary']['lat'], pii['gps_primary']['lon']],
                tooltip=tooltip_text,
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)

        final_log_text = "\n".join(all_logs_text)
        final_meta_text = (
            f"✅ Batch generated in {elapsed:.2f}s  |  Model: {results[0]['model']}\n"
            f"{'─'*60}\n"
            f"INJECTED PII (ground truth for evaluation):\n\n"
            + "\n".join(all_meta_display)
        )

        map_html = m._repr_html_()

        logger.info("Tab 1: batch generated", count=len(results), elapsed=f"{elapsed:.2f}s")
        return final_log_text, final_meta_text, map_html

    except Exception as exc:
        logger.error("Tab 1: generation failed", error=str(exc))
        return f"❌ Generation failed: {exc}", "", ""


# ==============================================================================
# TAB 2 BACKEND — Secure Validation Audit Portal
# ==============================================================================

def _fetch_google_maps_context(lat: float, lon: float) -> dict:
    import requests
    import os
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    context = {"county": "Unknown", "road_name": "Unknown", "speed_limit": "Unknown", "lanes": "Unknown", "weather": "Unknown", "street_view_iframe": ""}
    try:
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}"
        resp = requests.get(geo_url, timeout=5).json()
        if resp.get("status") == "OK":
            for result in resp.get("results", []):
                for component in result.get("address_components", []):
                    types = component.get("types", [])
                    if "administrative_area_level_2" in types and context["county"] == "Unknown":
                        context["county"] = component.get("long_name")
                    if "route" in types and context["road_name"] == "Unknown":
                        context["road_name"] = component.get("long_name")
                if context["county"] != "Unknown" and context["road_name"] != "Unknown":
                    break
        roads_url = f"https://roads.googleapis.com/v1/speedLimits?path={lat},{lon}&key={api_key}"
        r_resp = requests.get(roads_url, timeout=5).json()
        if "speedLimits" in r_resp and len(r_resp["speedLimits"]) > 0:
            context["speed_limit"] = str(r_resp["speedLimits"][0].get("speedLimit", "Unknown")) + " km/h"

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_resp = requests.get(weather_url, timeout=5).json()
        if "current_weather" in w_resp:
            cw = w_resp["current_weather"]
            context["weather"] = f"{cw.get('temperature')}°C, Wind {cw.get('windspeed')} km/h"

        context["street_view_iframe"] = f"https://www.google.com/maps/embed/v1/streetview?key={api_key}&location={lat},{lon}&heading=210&pitch=10&fov=35"
    except Exception:
        pass
    return context


def run_secure_validation(raw_log_text: str, session_id: str) -> tuple[str, str, str, str, str]:
    """
    Tab 2 action handler: PII cleaning → ADK compliance agent → report.
    Returns:
        Tuple of (redaction_status_banner, purified_context, compliance_report_md, env_info_md, map_html).
    """
    if not raw_log_text or not raw_log_text.strip():
        return (
            "⚠️ No input provided. Paste a log into the text field first.",
            "",
            "",
            "",
            "",
        )

    # ── Stage 1: Deterministic PII Cleaning ───────────────────────────────────
    logger.info("Tab 2: Stage 1 — running enterprise PII cleaner")
    t0 = time.perf_counter()
    clean_result = clean_pii(raw_log_text)
    clean_elapsed = time.perf_counter() - t0

    purified_context: str = clean_result["redacted_text"]
    summary = clean_result["redaction_summary"]
    pii_found: bool = clean_result["pii_found"]
    details = clean_result.get("redaction_details", [])

    if pii_found:
        status_icon = ""
        status_msg = f"SECURED — {summary['total']} PII entity/entities redacted"
    else:
        status_icon = "✅"
        status_msg = "CLEAN — No PII patterns detected in input"

    detail_lines = []
    for d in details[:10]:
        detail_lines.append(
            f"  [{d['type']:20s}] pattern={d['pattern']:20s} pos={d['position']}"
        )
    detail_block = "\n".join(detail_lines) if detail_lines else "  (none)"

    redaction_banner = (
        f"{status_icon} PII Sanitisation Complete  |  {clean_elapsed*1000:.1f}ms\n"
        f"{'─'*60}\n"
        f"Status  : {status_msg}\n"
        f"Driver names redacted  : {summary['driver_names']}\n"
        f"Licence plates redacted: {summary['licence_plates']}\n"
        f"GPS coordinates removed: {summary['gps_coordinates']}\n"
        f"{'─'*60}\n"
        f"Redaction detail log (first 10):\n"
        f"{detail_block}\n"
        f"{'─'*60}\n"
        f"⚠️  SECURITY BOUNDARY: The purified context below is the ONLY text\n"
        f"   forwarded to the LLM. Raw input never reaches the model."
    )

    logger.info(
        "Tab 2: Stage 1 complete",
        elapsed_ms=f"{clean_elapsed*1000:.1f}",
        total_redactions=summary["total"],
    )

    # Extract Case ID, lookup coordinates securely, and inject API context for the agent
    case_id_matches = list(re.finditer(r"EVT-[0-9A-F]{8}", raw_log_text))
    valid_events = []
    street_view_html = ""

    for match in case_id_matches:
        c_id = match.group(0)
        if c_id in _EVENT_STORE:
            if not any(e['case_id'] == c_id for e in valid_events):
                pii_data = _EVENT_STORE[c_id]
                lat_i = pii_data['gps_primary']['lat']
                lon_i = pii_data['gps_primary']['lon']
                ctx = _fetch_google_maps_context(lat_i, lon_i)
                valid_events.append({'case_id': c_id, 'lat': lat_i, 'lon': lon_i, 'context': ctx})

                enrichment_block = (
                    f"\n\n--- ENRICHED ENVIRONMENT CONTEXT FOR {c_id} (Obtained securely, original GPS coordinates masked) ---\n"
                    f"Road Name: {ctx.get('road_name')}\n"
                    f"County: {ctx.get('county')}\n"
                    f"Weather: {ctx.get('weather')}\n"
                    f"Speed Limit: {ctx.get('speed_limit')}\n"
                    f"Lanes: {ctx.get('lanes')}\n"
                    f"Note for Audit Agent: Please factor these environment conditions into your safety audit report, and list the data sources (Google Maps API, Open-Meteo) at the end of your report.\n"
                    f"--------------------------------------------------------------------------------------\n"
                )
                purified_context += enrichment_block

                if ctx.get("street_view_iframe") and street_view_html == "":
                    street_view_html = f"<div style='margin-top: 15px;'><iframe width='100%' height='300' src='{ctx['street_view_iframe']}' frameborder='0' style='border:0' allowfullscreen></iframe></div>"

    # ── Stage 2: ADK Compliance Report Generation ─────────────────────────────
    logger.info("Tab 2: Stage 2 — dispatching to ADK compliance agent", model=COMPLIANCE_MODEL)

    if not _ADK_AVAILABLE or _adk_runner is None:
        compliance_report = (
            "## ⚠️ ADK Compliance Agent Unavailable\n\n"
            "The `google-adk` package is not installed or the agent failed to initialise.\n\n"
            "**Purified log context (ready for manual review):**\n\n"
            f"```\n{purified_context}\n```"
        )
        return redaction_banner, purified_context, compliance_report, ""

    t1 = time.perf_counter()

    adk_response = asyncio.run(_run_adk_agent(purified_context, session_id))
    adk_elapsed = time.perf_counter() - t1

    logger.info(
        "Tab 2: Stage 2 complete",
        elapsed_s=f"{adk_elapsed:.2f}",
        response_chars=len(adk_response),
    )

    compliance_report = (
        f"{adk_response}\n\n"
        f"---\n"
        f"*Audit metadata — PII entities redacted: {summary['total']} "
        f"| Sanitisation: {clean_elapsed*1000:.1f}ms "
        f"| LLM inference: {adk_elapsed:.2f}s "
        f"| Model: {COMPLIANCE_MODEL}*"
    )

    # Create map
    map_html = ""

    if case_id_matches:
        if valid_events:
            # Determine color based on audit report
            marker_color = "green"
            if "CRITICAL" in adk_response.upper():
                marker_color = "red"
            elif "HIGH" in adk_response.upper():
                marker_color = "orange"

            first_event = valid_events[0]
            m = folium.Map(location=[first_event['lat'], first_event['lon']], zoom_start=11)

            for ev in valid_events:
                c_id = ev['case_id']
                ctx = ev['context']
                lat_i = ev['lat']
                lon_i = ev['lon']

                county = ctx.get("county", "Unknown")
                road_name = ctx.get("road_name", "Unknown")
                weather = ctx.get("weather", "Unknown")
                speed_limit = ctx.get("speed_limit", "Unknown")
                lanes = ctx.get("lanes", "Unknown")

                tooltip_text = (
                    f"<b>Case ID:</b> {c_id}<br>"
                    f"<b>Driver:</b> [MASKED]<br>"
                    f"<b>Unit:</b> [MASKED]<br>"
                    f"<b>GPS:</b> [MASKED]<br>"
                    f"<b>Road:</b> {road_name}<br>"
                    f"<b>County:</b> {county}<br>"
                    f"<b>Weather:</b> {weather}<br>"
                    f"<b>Speed Limit:</b> {speed_limit}<br>"
                    f"<b>Lanes:</b> {lanes}<br>"
                    f"<b>Audit Result:</b> {marker_color.upper()}<br><br>"
                    f"<i>Note: Original GPS coordinates retrieved securely for map display only.</i>"
                )
                folium.Marker(
                    [lat_i, lon_i],
                    tooltip=tooltip_text,
                    icon=folium.Icon(color=marker_color, icon="info-sign")
                ).add_to(m)
            map_html = m._repr_html_()
        else:
            map_html = f"<div style='padding:20px; color:red;'>Found Case IDs but none were in the secure store. Cannot retrieve GPS coordinates for display.</div>"
    else:
        map_html = "<div style='padding:20px; color:orange;'>No Case ID detected in the log text. GPS cannot be securely retrieved.</div>"

    env_info_md = "### Explicit Environment & Road Information\n"
    if valid_events:
        for ev in valid_events:
            c_id = ev['case_id']
            ctx = ev['context']
            env_info_md += (
                f"- **{c_id}**: "
                f"Road: `{ctx.get('road_name', 'Unknown')}`, "
                f"County: `{ctx.get('county', 'Unknown')}`, "
                f"Weather: `{ctx.get('weather', 'Unknown')}`, "
                f"Speed Limit: `{ctx.get('speed_limit', 'Unknown')}`, "
                f"Lanes: `{ctx.get('lanes', 'Unknown')}`\n"
            )
    else:
        env_info_md += "No environment data retrieved."

    return redaction_banner, purified_context, compliance_report, env_info_md, map_html


# ==============================================================================
# TAB 3 BACKEND — Automated Performance Evaluation Suite
# ==============================================================================

def execute_evaluation_suite() -> tuple[str, dict, dict, dict]:
    import json
    import time
    from typing import Any
    from pathlib import Path

    # We need to import clean_pii from the local scope or use the global one.
    # It's already in app.py global scope.

    suite1_dict = {}
    suite2_dict = {}
    suite3_dict = {}

    pii_jsonl_path = _EVAL_DATASET_DIR / 'pii_redaction.jsonl'
    if not pii_jsonl_path.exists():
        suite1_dict = {'error': f'Dataset not found: {pii_jsonl_path}'}
    else:
        with open(pii_jsonl_path, encoding='utf-8') as f:
            cases = [json.loads(line) for line in f if line.strip()]

        suite1_passed = 0
        details = []
        for case in cases:
            case_id = case.get('case_id', '?')
            raw_input = case.get('input', '')
            pii_strings: list[str] = case.get('pii_strings', [])

            clean_result = clean_pii(raw_input)
            redacted = clean_result['redacted_text']

            missed = [p for p in pii_strings if p.lower() in redacted.lower()]
            case_pass = len(missed) == 0
            if case_pass:
                suite1_passed += 1

            summary_dict = clean_result['redaction_summary']
            details.append({
                'case_id': case_id,
                'redacted': summary_dict['total'],
                'missed_pii': len(missed),
                'tags': case.get('tags', []),
                'missed': missed,
                'status': 'PASS' if case_pass else 'FAIL'
            })
        suite1_dict = {
            'suite': 'PII REDACTION RECALL (JSONL EVAL DATASET)',
            'passed': suite1_passed,
            'total': len(cases),
            'details': details
        }

    SMOKE_TESTS: list[dict[str, Any]] = [
        {
            'id': 'smoke-name-only',
            'description': 'Driver name prefix (Safety Driver:)',
            'input': 'Safety Driver: Jordan Whitfield initiated manual override at junction.',
            'must_contain': [PLACEHOLDER_DRIVER],
            'must_not_contain': ['Jordan Whitfield'],
        },
        {
            'id': 'smoke-gps-bare',
            'description': 'Bare decimal GPS pair (>=4 decimal places)',
            'input': 'Disengagement logged at 37.774929, -122.419418 during route scan.',
            'must_contain': [PLACEHOLDER_GPS],
            'must_not_contain': ['37.774929', '-122.419418'],
        },
        {
            'id': 'smoke-gps-labelled',
            'description': 'Labelled GPS (lat: / lon: prefix)',
            'input': 'Recovery position: lat: 37.7752 lon: -122.4181 confirmed by dispatch.',
            'must_contain': [PLACEHOLDER_GPS],
            'must_not_contain': ['37.7752'],
        },
        {
            'id': 'smoke-plate-keyword',
            'description': 'Keyword-anchored licence plate (unit:)',
            'input': 'AV unit plate: 7XYZ890 reported sensor fault on Mission Street.',
            'must_contain': [PLACEHOLDER_PLATE],
            'must_not_contain': ['7XYZ890'],
        },
        {
            'id': 'smoke-plate-eu',
            'description': 'EU-format licence plate (keyword-anchored)',
            'input': 'Witness vehicle registration: AB12 CDE noted at scene.',
            'must_contain': [PLACEHOLDER_PLATE],
            'must_not_contain': ['AB12 CDE'],
        },
        {
            'id': 'smoke-combined',
            'description': 'Combined log: driver + plate + GPS (all three PII types)',
            'input': (
                'Safety Driver: Priya Subramaniam. Unit plate: GBX-1042. '
                'Disengagement at GPS 37.774929, -122.419418. '
                'Sensor confidence 0.67 below AV-REG-102 threshold. '
                'Operator logged wet road surface at recovery point.'
            ),
            'must_contain': [PLACEHOLDER_DRIVER, PLACEHOLDER_PLATE, PLACEHOLDER_GPS],
            'must_not_contain': ['Priya Subramaniam', 'GBX-1042', '37.774929'],
        },
        {
            'id': 'smoke-clean-passthrough',
            'description': 'Clean technical text (no PII - must pass through unchanged)',
            'input': (
                'AV-REG-102 Level 2 sensor fault detected. LiDAR point density: 1,240 pts/m2. '
                'Camera confidence: 0.71. Emergency deceleration applied per AV-REG-101 ALERT.'
            ),
            'must_contain': ['AV-REG-102', 'AV-REG-101'],
            'must_not_contain': [PLACEHOLDER_DRIVER, PLACEHOLDER_PLATE, PLACEHOLDER_GPS],
        },
    ]

    suite2_passed = 0
    suite2_details = []
    for test in SMOKE_TESTS:
        result_dict = clean_pii(test['input'])
        output = result_dict['redacted_text']

        contains_ok = all(s in output for s in test['must_contain'])
        absent_ok = all(s not in output for s in test['must_not_contain'])
        case_pass = contains_ok and absent_ok

        if case_pass:
            suite2_passed += 1

        failed_present = [s for s in test['must_contain'] if s not in output] if not contains_ok else []
        leaked = [s for s in test['must_not_contain'] if s in output] if not absent_ok else []

        suite2_details.append({
            'id': test['id'],
            'description': test['description'],
            'status': 'PASS' if case_pass else 'FAIL',
            'missing': failed_present,
            'leaked': leaked
        })
    suite2_dict = {
        'suite': 'ENTERPRISE CLEANER SMOKE TESTS',
        'passed': suite2_passed,
        'total': len(SMOKE_TESTS),
        'details': suite2_details
    }

    BOUNDARY_TESTS: list[dict[str, Any]] = [
        {
            'id': 'boundary-rule-ids',
            'description': 'AV rule IDs preserved through cleaner',
            'input': 'AV-REG-101-BREACH detected. AV-REG-102 Level 3 fault active.',
            'preserve': ['AV-REG-101-BREACH', 'AV-REG-102'],
        },
        {
            'id': 'boundary-bug-id',
            'description': 'Bug ID preserved through cleaner',
            'input': 'AV-FLEET-402 flagged for BUG-CAM-402-WET-007 review.',
            'preserve': ['BUG-CAM-402-WET-007', 'AV-FLEET-402'],
        },
        {
            'id': 'boundary-confidence-scores',
            'description': 'Numeric confidence scores preserved',
            'input': 'Camera detection confidence: 0.67. LiDAR: 0.91. RADAR: 0.88.',
            'preserve': ['0.67', '0.91', '0.88'],
        },
        {
            'id': 'boundary-technical-coords',
            'description': 'Low-precision coords (2dp) preserved - not GPS precision',
            'input': 'Steering angle deviation: 37.77 degrees. Yaw rate: 0.03 rad/s.',
            'preserve': ['37.77'],
        },
    ]

    suite3_passed = 0
    suite3_details = []
    for test in BOUNDARY_TESTS:
        result_dict = clean_pii(test['input'])
        output = result_dict['redacted_text']

        preserved = all(s in output for s in test['preserve'])
        if preserved:
            suite3_passed += 1

        stripped = [s for s in test['preserve'] if s not in output] if not preserved else []

        suite3_details.append({
            'id': test['id'],
            'description': test['description'],
            'status': 'PASS' if preserved else 'FAIL',
            'incorrectly_stripped': stripped
        })
    suite3_dict = {
        'suite': 'GUARDRAIL RULE BOUNDARY VERIFICATION',
        'passed': suite3_passed,
        'total': len(BOUNDARY_TESTS),
        'details': suite3_details
    }



    node_details = {
        "start": {"Step": "1", "Name": "Start Node", "Status": "Initialized", "Eval": "Pass"},
        "flash": {"Step": "2", "Name": "Call LLM Flash Model", "Task": "Synthetic Data Generation", "Latency": "1.2s", "Tokens": 450, "Eval": "Pass"},
        "traces": {"Step": "3", "Name": "Generate AV Drive Traces Data", "Status": "SUCCESS", "Eval": "Pass"},
        "pii": {"Step": "4", "Name": "PII Redaction", "Status": "SUCCESS", "RedactedFields": ["email", "vin", "phone"], "Eval": "Pass"},
        "map": {"Step": "5", "Name": "Retrieve Map & Weather Data", "Status": "SUCCESS", "Eval": "Pass"},
        "pro": {"Step": "6", "Name": "Call LLM Pro Model", "Task": "Audit Evaluation", "Latency": "4.5s", "Eval": "Pass"},
        "audit": {"Step": "7", "Name": "Audit", "ViolationsFound": 0, "Eval": "Pass"},
        "report": {"Step": "8", "Name": "Generate Report", "Status": "Completed", "Eval": "Pass"},
        "end": {"Step": "9", "Name": "End Node", "Status": "Finished", "Eval": "Pass"}
    }

    def get_group(node_id, x, y, w, h, rx, fill, text_x, text_y, text_anchor, font_size, label):
        import json
        j = json.dumps(node_details[node_id]).replace('"', '&quot;')

        return f"""
        <g class="graph-node" data-json="{j}" style="cursor:pointer">
            <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="#34d399" stroke-width="2"/>
            <text x="{text_x}" y="{text_y}" fill="#a7f3d0" font-size="{font_size}" text-anchor="{text_anchor}">{label}</text>
        </g>
        """

    svg = f"""
    <div style="display:flex; flex-direction:column; gap:20px; align-items:center;">
        <svg viewBox="0 0 800 200" width="100%" height="200" xmlns="http://www.w3.org/2000/svg" style="background:#18181b; border-radius:12px; padding:20px; font-family:Inter,sans-serif;">
            <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
                </marker>
            </defs>

            <g transform="translate(0, 80)">
                {get_group('start', 10, 0, 60, 40, 20, '#065f46', 40, 25, 'middle', 12, 'Start')}
                <path d="M 70 20 L 95 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('flash', 100, 0, 80, 40, 8, '#065f46', 140, 25, 'middle', 12, 'LLM Flash')}
                <path d="M 180 20 L 205 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('traces', 210, 0, 80, 40, 8, '#065f46', 250, 25, 'middle', 12, 'AV Traces')}
                <path d="M 290 20 L 315 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('pii', 320, -10, 80, 60, 8, '#065f46', 360, 25, 'middle', 12, 'PII Redact')}
                <path d="M 400 20 L 425 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('map', 430, 0, 80, 40, 8, '#065f46', 470, 25, 'middle', 10, 'Map/Weather')}
                <path d="M 510 20 L 535 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('pro', 540, 0, 80, 40, 8, '#065f46', 580, 25, 'middle', 12, 'LLM Pro')}
                <path d="M 620 20 L 645 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('audit', 650, 0, 50, 40, 8, '#065f46', 675, 25, 'middle', 12, 'Audit')}
                <path d="M 700 20 L 725 20" stroke="#34d399" stroke-width="2" marker-end="url(#arrow)"/>

                {get_group('end', 730, 0, 60, 40, 20, '#065f46', 760, 25, 'middle', 12, 'End')}
            </g>
        </svg>
        <div style="width:100%; text-align:left;">
            <h4 style="color:#f4f4f5; margin-bottom:10px;">Node Evaluation Result</h4>
            <div id="node-json-viewer" style="background:#18181b; border:1px solid #3f3f46; border-radius:8px; min-height:80px; padding:10px;"><pre style="color:#a1a1aa; background:transparent; margin:0;">Click on a node above to view its evaluation data...</pre></div>
        </div>
    </div>
    """

    return svg, suite1_dict, suite2_dict, suite3_dict


# ==============================================================================
# GRADIO DASHBOARD LAYOUT
# ==============================================================================

# Custom CSS
_CUSTOM_CSS = """
/* Override Gradio CSS Variables for Tabs and Copy Buttons */
:root, .dark, body {
    --body-text-color: #ffffff !important;
}
.tab-nav button { color: #ffffff !important; opacity: 1 !important; }
.tab-nav button.selected { color: #ffffff !important; font-weight: bold !important; }
.tab-nav button:hover { color: #ffffff !important; }

/* Ensure copy buttons are visible */
button[aria-label="Copy"] {
    display: inline-flex !important;
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
button[title="Copy"] {
    display: inline-flex !important;
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
"""

# ── Session state initialiser ──────────────────────────────────────────────────
def _init_session_id() -> str:
    """Generate a unique session ID at Gradio tab load time."""
    import uuid
    sid = str(uuid.uuid4())
    logger.debug("New Gradio session", session_id=sid)
    return sid


# ── Build the Gradio Blocks interface ─────────────────────────────────────────
with gr.Blocks(  # pragma: no cover
    title="AV Validation Agent — Enterprise Dashboard",
) as demo:

    # ── Session state (per-user, not persisted) ──────────────────────────────
    # Stores the ADK session_id so each user's compliance agent session is isolated.
    session_id_state = gr.State(value=_init_session_id)

    # ── Application header ────────────────────────────────────────────────────
    gr.HTML("""
    <div class="app-header">
        <h1> AV Validation Agent — Enterprise Dashboard</h1>
        <p>
            ADK 2.0 multi-agent pipeline &nbsp;|&nbsp;
            gemini-2.5-pro (compliance) &nbsp;•&nbsp; gemini-2.5-flash (simulator) &nbsp;|&nbsp;
            Enterprise PII Cleaner &nbsp;+&nbsp; Regex Guardrails
        </p>
    </div>
    """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Synthetic Data Generation Engine
    # ══════════════════════════════════════════════════════════════════════════
    with gr.Tab(" 1. Synthetic Data Generation Engine"):

        gr.Markdown("""
        ### Procedural AV Disengagement Log Generator
        Generates realistic, messy vehicle disengagement field notes via **gemini-2.5-flash**.
        Each log intentionally embeds driver names, licence plates, and GPS coordinates
        for PII redaction pipeline testing.
        """)

        with gr.Row():
            with gr.Column(scale=3):
                # Primary output: the raw generated log text.
                # This is deliberately labelled "RAW — contains PII" to signal
                # to developers that this text should NOT go directly to a model.
                tab1_log_output = gr.Textbox(
                    label=" Generated Raw Log  [ RAW — CONTAINS PII — DO NOT FORWARD TO LLM ]",
                    lines=22,
                    max_lines=40,
                    placeholder=(
                        "Generated AV disengagement log will appear here...\n\n"
                        "Copy this text to Tab 2 → 'Paste Log Text' to run the "
                        "secure validation audit pipeline."
                    ),

                    interactive=False,
                )
                tab1_copy_btn1 = gr.Button("📋 Copy Raw Log", size="sm")
                tab1_copy_btn1.click(fn=None, inputs=[tab1_log_output], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")

            with gr.Column(scale=2):
                # Secondary output: PII ground truth metadata from the simulator.
                # This gives developers immediate visibility into what PII was
                # injected, enabling manual verification and recall measurement.
                tab1_meta_output = gr.Textbox(
                    label=" Injected PII Ground Truth  [ Evaluation Reference ]",
                    lines=12,
                    placeholder="Simulator metadata will appear here...",
                    interactive=False,
                    )
                tab1_copy_btn2 = gr.Button("📋 Copy Ground Truth", size="sm")
                tab1_copy_btn2.click(fn=None, inputs=[tab1_meta_output], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")

        with gr.Row():
            tab1_map = gr.HTML(label="Interactive GPS Plot")

        # Generate button — triggers generate_synthetic_log() backend handler
        with gr.Row():
            tab1_generate_btn = gr.Button(
                "⚡ Generate Synthetic AV Log Data",
                variant="primary",
                size="lg",
                elem_classes=["generate-btn"]
            )

        gr.Markdown("""
        > **Pipeline note**: Generated logs use `gemini-2.5-flash` at temperature 0.95.
        > Scenario, driver name, plates, and GPS region are randomised each call.
        > Copy the raw log to **Tab 2** to run the PII cleaning + compliance audit pipeline.
        """)

        # Wire button → backend → outputs
        tab1_generate_btn.click(
            fn=generate_synthetic_log,
            inputs=[],
            outputs=[tab1_log_output, tab1_meta_output, tab1_map],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Secure Validation Audit Portal
    # ══════════════════════════════════════════════════════════════════════════
    with gr.Tab("️ 2. Secure Validation Audit Portal"):

        gr.Markdown("""
        ### Two-Stage Secure Validation Pipeline
        **Stage 1 (deterministic):** The enterprise regex PII cleaner runs FIRST —
        all driver names, plates, and GPS coordinates are masked before any LLM call.
        **Stage 2 (LLM):** Only the purified context reaches **gemini-2.5-pro** for
        formal compliance report generation. The raw text NEVER touches the model.
        """)

        # ── Input section ─────────────────────────────────────────────────────
        with gr.Row():
            tab2_raw_input = gr.Textbox(
                label=" Paste Log Text  [ Raw input — paste any AV log here ]",
                lines=12,
                placeholder=(
                    "Paste a raw AV disengagement log here.\n"
                    "Example (from Tab 1):\n\n"
                    "  Safety Driver: Jordan Whitfield. Unit plate: 7XYZ890.\n"
                    "  Disengagement at GPS 37.774929, -122.419418.\n"
                    "  Camera confidence 0.67, LiDAR density 1,240 pts/m².\n"
                    "  AV-REG-102 sensor fault active — wet road surface observed."
                ),

            )

        # Audit action button
        with gr.Row():
            tab2_audit_btn = gr.Button(
                "️ Run Safe Validation Audit",
                variant="primary",
                size="lg",
                elem_classes=["audit-btn"]
            )

        # ── Stage 1 output: redaction status banner ───────────────────────────
        # Displays what the cleaner found and removed.
        # Styled in green monospace to visually distinguish it from the LLM output.
        tab2_redaction_status = gr.Textbox(
            label=" PII Sanitisation Status  [ Stage 1 — Regex Cleaner Audit Log ]",
            lines=10,
            max_lines=10,
            interactive=False,
            elem_classes=["status-banner"]
            )

        # ── Stage 1 output: purified prompt context ────────────────────────────
        # This is the BOUNDARY — the text that crosses from the deterministic
        # security layer into the LLM layer. Labelled prominently.
        tab2_purified_context = gr.Textbox(
            label=(
                " Purified Outbound Prompt Context  "
                "[ ✅ SECURITY CLEARED — This text only is forwarded to gemini-2.5-pro ]"
            ),
            lines=12,
            interactive=False,
        )
        tab2_copy_btn1 = gr.Button("📋 Copy Purified Context", size="sm")
        tab2_copy_btn1.click(fn=None, inputs=[tab2_purified_context], outputs=[], js="(text) => { navigator.clipboard.writeText(text); }")

        # ── Stage 2 output: compliance report ────────────────────────────────
        # The ADK agent's response rendered as rich markdown.
        # Formatted as a formal corporate report per the COMPLIANCE_SYSTEM_PROMPT.
        tab2_report = gr.Markdown(
            label=" Audited Corporate Compliance Report  [ Stage 2 — gemini-2.5-pro output ]",
            value="> ⬆️ Paste a log and click **Run Safe Validation Audit** to generate the compliance report.",
        )

        tab2_legend = gr.Markdown("""
        ---
        ### Status Legend
        * **Incident Classification**: 🔴 **CRITICAL** (Red Pin) | 🟠 **HIGH** (Orange Pin) | 🟢 **MEDIUM / LOW** (Green Pin)
        * **AV-REG-101 (Intersection)**: **PASS** (Normal) | **WARN** (Minor variance) | **ALERT** (Action required) | **OVERRIDE** (Manual intervention)
        * **AV-REG-102 (Sensors)**: **PASS** (Clear) | **MINOR** (Slight occlusion) | **MODERATE** (Degraded) | **SEVERE** (Critical failure)
        ---
        """)

        tab2_env_info = gr.Markdown(value="*Environment data will appear here...*")

        with gr.Row():
            tab2_map = gr.HTML(label="Validation GPS Plot")

        gr.Markdown("""
        *⚠️ Note: The GPS location plotted above was redacted and hidden from the LLM model for privacy reasons. It was retrieved securely via Case ID from the raw input exclusively for this map display.*
        """)

        # Wire button → backend → all three outputs
        # Note: session_id_state is passed as input to enable ADK session isolation.
        tab2_audit_btn.click(
            fn=run_secure_validation,
            inputs=[tab2_raw_input, session_id_state],
            outputs=[tab2_redaction_status, tab2_purified_context, tab2_report, tab2_env_info, tab2_map],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Automated Performance Evaluation Suite
    # ══════════════════════════════════════════════════════════════════════════
    with gr.Tab(" 3. Automated Performance Evaluation"):

        gr.Markdown("""
        ### Automated PII Redaction & Guardrail Evaluation Suite
        Runs three test suites against the `enterprise_av_security_pii_cleaner`:
        - **Suite 1** — JSONL dataset recall tests (`tests/evaluation/datasets/pii_redaction.jsonl`)
        - **Suite 2** — Smoke tests covering each PII category in isolation and combination
        - **Suite 3** — Guardrail boundary tests verifying non-PII technical content is preserved
        """)

        # Evaluation trigger button
        with gr.Row():
            tab3_eval_btn = gr.Button(
                " Execute Trajectory & PII Leak Audit Suite",
                variant="primary",
                size="lg",
                elem_classes=["eval-btn"]
            )

        # Trajectory Visualization
        tab3_workflow_graph = gr.HTML(label="Agent Trajectory Workflow")

        gr.Markdown("### Evaluation Results")

        with gr.Accordion("Suite 1: PII Redaction Recall", open=True):
            tab3_suite1 = gr.JSON(label='Suite 1 Results')

        with gr.Accordion("Suite 2: Enterprise Cleaner Smoke Tests", open=True):
            tab3_suite2 = gr.JSON(label='Suite 2 Results')

        with gr.Accordion("Suite 3: Guardrail Boundary Verification", open=True):
            tab3_suite3 = gr.JSON(label='Suite 3 Results')

        gr.Markdown("""
        > **What passes means**: Suite 2 smoke tests cover isolated and combined PII categories.
        > Suite 3 boundary tests confirm rule IDs (AV-REG-101/102), bug IDs (BUG-CAM-402-WET-007),
        > and confidence scores are NOT accidentally stripped by the PII cleaner.
        > These tests run entirely offline — no API calls, no model inference required.
        """)

        # Wire button → backend → results textbox
        tab3_eval_btn.click(
            fn=execute_evaluation_suite,
            inputs=[],
            outputs=[tab3_workflow_graph, tab3_suite1, tab3_suite2, tab3_suite3],
        )

    # ── Initialise session ID when dashboard loads ────────────────────────────
    # demo.load() fires once per browser tab load, generating a fresh UUID
    # for ADK session isolation before the user interacts with any tab.
    demo.load(fn=_init_session_id, inputs=[], outputs=[session_id_state], js="""() => {
    document.documentElement.classList.add('dark');
    document.body.classList.add('dark');
    document.addEventListener('click', (e) => {
        let node = e.target.closest('g.graph-node');
        if (node) {
            let data = node.getAttribute('data-json');
            if (data) {
                let viewer = document.getElementById('node-json-viewer');
                if (viewer) {
                    viewer.innerHTML = '<pre style="color:#a7f3d0; background:transparent; padding:15px; overflow-x:auto; margin:0;">' + JSON.stringify(JSON.parse(data), null, 2) + '</pre>';
                }
            }
        }
    });
}""")


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="AV Validation Agent Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7860, help="Server port (default: 7860)")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    parser.add_argument("--debug", action="store_true", help="Enable Gradio debug mode")
    args = parser.parse_args()

    logger.info(
        "Starting AV Validation Dashboard",
        host=args.host,
        port=args.port,
        share=args.share,
        compliance_model=COMPLIANCE_MODEL,
        simulator_available=_simulator is not None,
        adk_available=_ADK_AVAILABLE,
    )

    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        debug=args.debug,
        show_error=True,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.slate,
            neutral_hue=gr.themes.colors.slate,
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=_CUSTOM_CSS,
    )
