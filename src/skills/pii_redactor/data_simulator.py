"""
src/skills/pii_redactor/data_simulator.py

AV Disengagement Log Simulator
================================
Uses the Gemini API (gemini-1.5-flash) to procedurally generate realistic,
messy vehicle disengagement text logs on demand.

Each generated log intentionally contains:
  - Random human safety driver names
  - Vehicle licence plate numbers
  - Decimal GPS coordinates (lat/lon pairs)
  - Raw engineering field notes mixing technical jargon and informal observation

Purpose: Feed the enterprise_av_security_pii_cleaner with realistic test inputs
and generate evaluation datasets for the PII redaction pipeline.

Usage:
  python -m src.skills.pii_redactor.data_simulator
  python -m src.skills.pii_redactor.data_simulator --count 5 --save
  python -m src.skills.pii_redactor.data_simulator --seed 42

Environment:
  Requires GEMINI_API_KEY in .env (auto-loaded via python-dotenv).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

logger = structlog.get_logger(__name__)

# ── Gemini import ─────────────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.warning(
        "google-generativeai not installed. "
        "Install with: pip install google-generativeai"
    )

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL_ID = "gemini-1.5-flash"

# Disengagement scenario seeds for variety
_SCENARIO_SEEDS = [
    "unexpected pedestrian jaywalking near the ego vehicle at a four-way stop",
    "sudden lane change by a large truck causing sensor occlusion",
    "traffic light with conflicting signals at a complex downtown intersection",
    "wet road surface causing camera reflection artefacts at dusk",
    "construction zone with temporary lane markings obscuring road boundaries",
    "emergency vehicle approaching with sirens from a side street",
    "a cyclist weaving between traffic lanes in a high-speed urban corridor",
    "vehicle stall ahead causing rapid queue buildup on a motorway on-ramp",
    "school zone with children crossing outside of a designated crossing point",
    "heavy rain reducing LiDAR effective range below operational threshold",
    "object detected on road surface that did not resolve as obstacle within timeout",
    "roundabout entry with no clear yield gap — system held position for 18 seconds",
]

# Pool of realistic US/EU plate formats for the prompt
_PLATE_EXAMPLES = [
    "7XYZ890", "AB12 CDE", "CA 3ABC021", "LM-4921-N", "MXY-7734",
    "GBX-1042", "5KLM923", "TZ 88-432", "WQ21 JKL", "4RST612",
]

# Pool of driver name seeds (diverse, realistic)
_DRIVER_NAME_SEEDS = [
    "Jordan Whitfield", "Priya Subramaniam", "Carlos Mendez-Torres",
    "Fatima Al-Hassan", "Li Wei", "Sam O'Brien", "Aisha Nkrumah",
    "Thomas Eriksson", "Yuki Tanaka", "Maria dos Santos",
    "Ravi Krishnamurthy", "Elena Vasquez", "David Okonkwo",
    "Sophie Beaumont", "Omar Abdullah", "Ingrid Lindström",
    "James Obi-Chen", "Nadia Petrov", "Alex Rivera-Garcia",
    "Amara Diallo",
]

# GPS coordinate regions (Los Angeles area for realism)
_GPS_REGIONS = [
    {"name": "downtown_la", "lat_range": (34.040, 34.060), "lon_range": (-118.260, -118.240)},
    {"name": "santa_monica", "lat_range": (34.010, 34.030), "lon_range": (-118.500, -118.480)},
    {"name": "hollywood", "lat_range": (34.090, 34.110), "lon_range": (-118.340, -118.320)},
    {"name": "pasadena", "lat_range": (34.140, 34.160), "lon_range": (-118.150, -118.130)},
    {"name": "long_beach", "lat_range": (33.760, 33.780), "lon_range": (-118.200, -118.180)},
]


# ==============================================================================
# Log Generation Prompt
# ==============================================================================

def _build_generation_prompt(
    scenario: str,
    driver_name: str,
    plate_1: str,
    plate_2: str,
    lat: float,
    lon: float,
    lat2: float,
    lon2: float,
    timestamp: str,
    fleet_unit: str,
    case_id: str,
) -> str:
    """
    Construct the Gemini generation prompt for a single disengagement log.

    The prompt instructs the model to produce a raw, messy, realistic log
    that intentionally includes PII mixed with engineering field notes.
    """
    return f"""You are a simulation engine generating realistic raw AV disengagement logs
for a self-driving vehicle safety research dataset.

Generate a single, authentic-looking vehicle disengagement incident report.
The report should look like it was written hastily in the field by a safety driver
and then partially cleaned up by an engineering intern — so it is messy, inconsistent,
mixes informal and technical language, and contains abbreviations.

MANDATORY: The report MUST include ALL of the following PII elements, embedded
naturally in the text (not as a structured list):

1. DRIVER NAME: {driver_name}
   - Use this exact name. Reference it at least twice using different formats,
     e.g. full name once, then just first or last name, or as "SD {driver_name.split()[0]}".
   - Use at least one of these prefix patterns: "Safety Driver:", "SD", "Operator:",
     "Reported by:", "Driver", "Engineer" followed by the name.

2. VEHICLE PLATES:
   - Primary unit plate: {plate_1}  (the AV unit itself)
   - Witness/nearby vehicle plate: {plate_2}  (observed during incident)
   - Reference each plate naturally (e.g. "unit plate {plate_1}", "reg: {plate_2}",
     "vehicle {plate_1}", "plate of nearby car: {plate_2}")

3. GPS COORDINATES:
   - Disengagement location: {lat:.6f}, {lon:.6f}
   - A secondary waypoint or recovery position: {lat2:.6f}, {lon2:.6f}
   - Use different notation for each: one as a bare decimal pair, one with a
     label like "GPS:", "lat/lon:", "pos:", "coord:", or "location:"

4. EVENT ID: {case_id}
   - Must explicitly include "Case ID: {case_id}" somewhere in the log.

SCENARIO: {scenario}

ADDITIONAL CONTEXT:
   - Timestamp: {timestamp}
   - Fleet unit: {fleet_unit}
   - Mix in 2-3 of these technical observations naturally:
     * camera confidence degradation (specific values like 0.67 or 0.71)
     * LiDAR point density reading
     * vehicle speed at disengagement (km/h)
     * weather/road surface condition
     * AV-REG-101 or AV-REG-102 reference (cite the rule ID naturally)
     * sensor module version or patch ID

FORMAT RULES:
   - Write as a single free-text block (no JSON, no structured headers)
   - 200-350 words total
   - Include at least one typo or abbreviation that looks authentic
   - Do NOT use bullet points or numbered lists — pure prose or rough notes style
   - End with a signature line: "Submitted by [full name], [title/role]"

Generate the report now:"""


# ==============================================================================
# Simulator Class
# ==============================================================================

class AVDisengagementLogSimulator:
    """
    Procedurally generates messy AV disengagement logs via Gemini 1.5 Flash.

    Each call to `generate()` produces a unique log with randomised PII
    (driver name, plates, GPS coordinates) and a randomised scenario.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        temperature: float = 0.95,
        max_output_tokens: int = 600,
    ) -> None:
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._model: Optional[object] = None

        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-generativeai is required. "
                "Install with: pip install google-generativeai"
            )

        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in .env or pass api_key= explicitly."
            )

        genai.configure(api_key=resolved_key)  # type: ignore[attr-defined]
        self._model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name=MODEL_ID,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
                "candidate_count": 1,
            },
        )
        logger.info("AVDisengagementLogSimulator initialised", model=MODEL_ID)

    def _random_gps(self, region: dict) -> tuple[float, float]:
        """Generate a random lat/lon within the specified region."""
        lat = random.uniform(*region["lat_range"])
        lon = random.uniform(*region["lon_range"])
        return round(lat, 6), round(lon, 6)

    def generate(self, seed: Optional[int] = None) -> dict:
        """
        Generate a single synthetic AV disengagement log.

        Args:
            seed: Optional random seed for reproducibility.

        Returns:
            Dict with:
              - log_text (str): The generated messy log (contains PII).
              - metadata (dict): The PII ground truth injected into the prompt
                                 (for evaluation dataset construction).
              - generated_at (str): ISO 8601 timestamp.
              - model (str): Model ID used.
        """
        if seed is not None:
            random.seed(seed)

        # Randomise all variables
        scenario = random.choice(_SCENARIO_SEEDS)
        driver_name = random.choice(_DRIVER_NAME_SEEDS)
        plate_1 = random.choice(_PLATE_EXAMPLES)
        plate_2 = random.choice([p for p in _PLATE_EXAMPLES if p != plate_1])
        region_1 = random.choice(_GPS_REGIONS)
        region_2 = random.choice(_GPS_REGIONS)
        lat1, lon1 = self._random_gps(region_1)
        lat2, lon2 = self._random_gps(region_2)

        fleet_units = [f"AV-FLEET-{n}" for n in [399, 400, 401, 402, 403]]
        fleet_unit = random.choice(fleet_units)

        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        import uuid
        case_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"

        prompt = _build_generation_prompt(
            scenario=scenario,
            driver_name=driver_name,
            plate_1=plate_1,
            plate_2=plate_2,
            lat=lat1,
            lon=lon1,
            lat2=lat2,
            lon2=lon2,
            timestamp=timestamp,
            fleet_unit=fleet_unit,
            case_id=case_id,
        )

        logger.debug(
            "Generating disengagement log",
            scenario=scenario[:50],
            driver=driver_name,
            plate_1=plate_1,
            gps=f"{lat1},{lon1}",
        )

        response = self._model.generate_content(prompt)  # type: ignore[union-attr]
        log_text: str = response.text.strip()

        metadata = {
            "scenario": scenario,
            "injected_pii": {
                "case_id": case_id,
                "driver_name": driver_name,
                "plate_primary": plate_1,
                "plate_witness": plate_2,
                "gps_primary": {"lat": lat1, "lon": lon1, "region": region_1["name"]},
                "gps_secondary": {"lat": lat2, "lon": lon2, "region": region_2["name"]},
            },
            "fleet_unit": fleet_unit,
            "model": MODEL_ID,
            "temperature": self.temperature,
        }

        logger.info(
            "Disengagement log generated",
            char_count=len(log_text),
            fleet_unit=fleet_unit,
        )

        return {
            "log_text": log_text,
            "metadata": metadata,
            "generated_at": timestamp,
            "model": MODEL_ID,
        }

    def generate_batch(self, count: int = 5, seed: Optional[int] = None) -> list[dict]:
        """
        Generate `count` unique disengagement logs.

        Args:
            count: Number of logs to generate (1–50).
            seed: Optional base seed; each log uses seed+i for reproducibility.

        Returns:
            List of log dicts from `generate()`.
        """
        count = max(1, min(count, 50))
        results = []
        for i in range(count):
            log_seed = (seed + i) if seed is not None else None
            result = self.generate(seed=log_seed)
            results.append(result)
            logger.info(f"Generated log {i + 1}/{count}")
        return results


# ==============================================================================
# CLI Interface
# ==============================================================================

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic AV disengagement logs with embedded PII",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 1 log and print to stdout
  python -m src.skills.pii_redactor.data_simulator

  # Generate 5 logs and save to JSONL file
  python -m src.skills.pii_redactor.data_simulator --count 5 --save

  # Generate reproducibly with seed
  python -m src.skills.pii_redactor.data_simulator --count 3 --seed 42 --save

  # Pipe into the PII cleaner
  python -m src.skills.pii_redactor.data_simulator | python -c "
    import sys, json
    from src.skills.pii_redactor.enterprise_av_security_pii_cleaner import clean_pii
    data = json.load(sys.stdin)
    print(clean_pii(data['log_text'])['redacted_text'])
  "
""",
    )
    parser.add_argument("--count", type=int, default=1, help="Number of logs to generate (default: 1)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--save", action="store_true", help="Save output to JSONL in tests/evaluation/datasets/")
    parser.add_argument("--temperature", type=float, default=0.95, help="Generation temperature (default: 0.95)")
    parser.add_argument("--print-metadata", action="store_true", help="Print injected PII metadata alongside log")
    args = parser.parse_args()

    try:
        simulator = AVDisengagementLogSimulator(temperature=args.temperature)
    except (ImportError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.count == 1:
        result = simulator.generate(seed=args.seed)
        results = [result]
    else:
        results = simulator.generate_batch(count=args.count, seed=args.seed)

    # Print to stdout
    for i, r in enumerate(results, 1):
        if args.count > 1:
            print(f"\n{'=' * 70}")
            print(f"LOG {i}/{args.count} — {r['generated_at']}")
            print("=" * 70)
        print(r["log_text"])
        if args.print_metadata:
            print("\n--- INJECTED PII METADATA ---")
            print(json.dumps(r["metadata"]["injected_pii"], indent=2))

    # Optionally save
    if args.save:
        out_dir = (
            Path(__file__).parent.parent.parent.parent
            / "tests" / "evaluation" / "datasets"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = out_dir / f"simulated_logs_{ts}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n✅ Saved {len(results)} log(s) to: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    _cli()
