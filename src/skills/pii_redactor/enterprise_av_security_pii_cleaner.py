"""
src/skills/pii_redactor/enterprise_av_security_pii_cleaner.py

Enterprise AV Security PII Cleaner
====================================
Tool name : enterprise_av_security_pii_cleaner
Manifest  : src/skills/pii_redactor/skill.md

A deterministic, regex-driven PII sanitisation tool for autonomous vehicle
disengagement logs and safety driver field notes.

Targets three PII categories specific to AV operational data:
  1. Human driver names   → [DRIVER_REDACTED]
  2. Vehicle licence plates → [PLATE_REDACTED]
  3. Decimal GPS coordinate pairs → [GPS_REDACTED]

Design principles:
  - Zero LLM inference — pure regex, deterministic, reproducible
  - Contextual matching — name patterns anchored to known AV log prefixes
  - Defence-in-depth positioning — runs BEFORE Presidio and BEFORE any LLM call
  - Typed placeholders — each PII category gets a distinct token for auditability

ADK FunctionTool registration:
  See src/agent/agent.py — register as FunctionTool(func=clean_pii)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

import structlog

logger = structlog.get_logger(__name__)


# ==============================================================================
# Redaction Placeholder Tokens
# ==============================================================================

PLACEHOLDER_DRIVER: str = "[DRIVER_REDACTED]"
PLACEHOLDER_PLATE: str = "[PLATE_REDACTED]"
PLACEHOLDER_GPS: str = "[GPS_REDACTED]"


# ==============================================================================
# Regex Pattern Definitions
# ==============================================================================

# ── 1. Driver Name Patterns ───────────────────────────────────────────────────
#
# Strategy: anchor on known AV log prefixes, then capture a name token.
# Name token = optional title (Mr/Ms/Dr/Mrs/Mx) + 1–2 capitalised word(s).
#
# Covered prefix keywords (case-insensitive):
#   Safety Driver, SD, Driver, Operator, Technician, Tech, Engineer,
#   Pilot, Supervisor, Attendant, Occupant, Personnel
#
# Matches:
#   "Safety Driver: John Ramirez"         → prefix colon + name
#   "SD Alice Chen-Park"                   → prefix space + name
#   "Driver = Mr. Thomas Nguyen"           → prefix equals + name
#   "Operator (Dr. Fatima Al-Hassan)"      → prefix paren + name

_TITLE = r"(?:Mr\.?|Ms\.?|Mrs\.?|Dr\.?|Mx\.?|Prof\.?)\s+"
_NAME_WORD = r"[A-Z][a-zA-Zéèêàâùûôîïëæœç'\-]{1,30}"
_NAME_TOKEN = rf"(?:{_TITLE})?{_NAME_WORD}(?:\s+{_NAME_WORD}){{0,2}}"

_DRIVER_PREFIXES = (
    r"(?:Safety\s+Driver|Safety\s+Op(?:erator)?|SD|Driver|Operator|"
    r"Technician|Tech|Engineer|Pilot|Supervisor|Attendant|Occupant|Personnel|"
    r"Disengagement\s+by|Reported\s+by|Logged\s+by|Submitted\s+by)"
)

_DRIVER_PATTERN = re.compile(
    rf"({_DRIVER_PREFIXES})"           # Group 1: prefix keyword
    rf"(?:\s*[:\-=\(]\s*|\s+)"        # Separator: colon / dash / equals / paren / space
    rf"({_NAME_TOKEN})",               # Group 2: the name (will be replaced)
    re.IGNORECASE,
)


# ── 2. Vehicle Licence Plate Patterns ─────────────────────────────────────────
#
# Strategy: keyword-anchored + standalone plate-shaped tokens.
#
# Covered formats:
#   US standard   : ABC-1234, ABC 1234, 1234ABC, 7XYZ123
#   EU/UK         : AB12 CDE, AB 12 CDE
#   California    : 1ABC234
#   Alphanumeric  : ZZZ-999, AA-0000
#
# Keyword anchors: plate, license, licence, reg, unit, vehicle, fleet, veh
#
# Note: plates are bounded by word boundaries to avoid matching hex strings
#       or other technical tokens in log data.

_PLATE_FORMATS = (
    r"[A-Z]{1,3}[\s\-]?\d{1,4}[\s\-]?[A-Z]{0,3}"   # ABC-1234, AB12CDE
    r"|"
    r"\d{1,4}[\s\-]?[A-Z]{1,4}[\s\-]?\d{0,4}"       # 1234ABC, 1ABC234
    r"|"
    r"[A-Z0-9]{2,4}[\s\-][A-Z0-9]{2,4}(?:[\s\-][A-Z0-9]{2,4})?"  # EU multi-part
)

_PLATE_KEYWORD = (
    r"(?:plate|license\s+plate|licence\s+plate|lic(?:ence|ense)?|"
    r"reg(?:istration)?|unit|fleet\s+id|veh(?:icle)?(?:\s+id)?)"
)

# Keyword-anchored plate: "plate: 7ABC123" or "unit 7ABC123"
_PLATE_ANCHORED_PATTERN = re.compile(
    rf"({_PLATE_KEYWORD})"
    rf"(?:\s*[:\-=\s]\s*)"
    rf"({_PLATE_FORMATS})",
    re.IGNORECASE,
)

# Standalone plate: any token that looks like a plate (less aggressive)
# Bounded to avoid false positives in hex/sensor IDs
_PLATE_STANDALONE_PATTERN = re.compile(
    r"\b([A-Z]{1,3}[\-\s]\d{2,4}[\-\s]?[A-Z]{0,3}|"
    r"\d{1,4}[A-Z]{2,4}\d{0,4})\b",
    re.IGNORECASE,
)


# ── 3. Decimal GPS Coordinate Patterns ────────────────────────────────────────
#
# Strategy: match decimal degree pairs (lat, lon) with and without keyword prefix.
#
# Covered forms:
#   "37.774900, -122.419400"              → bare pair
#   "lat: 37.7749 lon: -122.4194"         → labelled
#   "GPS(37.774900,-122.419400)"          → function-call style
#   "position=(37.774929, -122.419418)"   → assignment style
#   "loc: 37.7749N 122.4194W"            → compass suffix (N/S/E/W)
#
# Latitude range  : -90.0000 to +90.0000
# Longitude range : -180.0000 to +180.0000

_LAT = r"[+\-]?(?:90(?:\.0{1,8})?|[0-8]?\d(?:\.\d{1,8})?)"
_LON = r"[+\-]?(?:180(?:\.0{1,8})?|1[0-7]\d(?:\.\d{1,8})?|\d{1,2}(?:\.\d{1,8})?)"
_COMPASS = r"[NSEWnsew]?"

# Keyword prefixes for GPS
_GPS_KEYWORD = (
    r"(?:gps|lat(?:itude)?|lon(?:gitude)?|lng|position|pos|"
    r"location|loc|coord(?:inate)?s?|waypoint)"
)

# Pair pattern: lat, lon (comma-separated, optional whitespace)
_GPS_PAIR = rf"({_LAT}{_COMPASS})\s*[,;]\s*({_LON}{_COMPASS})"

# Labelled pair: "lat: 37.77 lon: -122.41"
_GPS_LABELLED_PATTERN = re.compile(
    r"(?:lat(?:itude)?)\s*[:\-=]?\s*"
    rf"({_LAT}{_COMPASS})"
    r"[\s,;]+"
    r"(?:lon(?:gitude)?|lng)\s*[:\-=]?\s*"
    rf"({_LON}{_COMPASS})",
    re.IGNORECASE,
)

# Keyword-prefixed pair: "GPS 37.77, -122.41" or "pos=(37.77, -122.41)"
_GPS_KEYWORD_PATTERN = re.compile(
    rf"{_GPS_KEYWORD}"
    rf"[\s:=\(]*"
    rf"{_GPS_PAIR}"
    rf"\)?",
    re.IGNORECASE,
)

# Bare decimal pair: "37.774900, -122.419400" (6+ decimal places = high precision)
_GPS_BARE_PATTERN = re.compile(
    r"\b"
    rf"([+\-]?(?:90(?:\.0{{6,8}})?|[0-8]?\d\.\d{{4,8}}))"  # lat (>=4 decimals)
    r"\s*[,;]\s*"
    rf"([+\-]?(?:180(?:\.0{{6,8}})?|1[0-7]\d\.\d{{4,8}}|\d{{1,2}}\.\d{{4,8}}))"  # lon
    r"\b",
    re.IGNORECASE,
)


# ==============================================================================
# Result Dataclass
# ==============================================================================

@dataclass
class CleanerResult:
    """Structured output from enterprise_av_security_pii_cleaner."""

    original_text: str
    redacted_text: str
    driver_name_count: int = 0
    licence_plate_count: int = 0
    gps_coordinate_count: int = 0
    redaction_details: List[dict] = field(default_factory=list)

    @property
    def total_redactions(self) -> int:
        return self.driver_name_count + self.licence_plate_count + self.gps_coordinate_count

    @property
    def pii_found(self) -> bool:
        return self.total_redactions > 0


# ==============================================================================
# Core Redaction Engine
# ==============================================================================

class EnterpriseAVSecurityPIICleaner:
    """
    Deterministic regex-based PII cleaner for AV disengagement logs.

    Processes text in three sequential passes:
      Pass 1 — GPS coordinates   (removed first to avoid coordinate digits
                                   being mistaken for plate numbers)
      Pass 2 — Licence plates    (before name pass to avoid plate tokens
                                   being partially matched by name regex)
      Pass 3 — Driver names      (last, as prefixes are most specific)
    """

    def __init__(self) -> None:
        self._driver_name_count = 0
        self._plate_count = 0
        self._gps_count = 0
        self._details: List[dict] = []

    # ── Pass 1: GPS Coordinates ───────────────────────────────────────────────

    def _redact_gps(self, text: str) -> str:
        """Replace decimal GPS coordinate pairs with [GPS_REDACTED]."""

        def _replace_gps(match: re.Match, label: str) -> str:
            self._gps_count += 1
            self._details.append({
                "type": "GPS_COORDINATE",
                "match": match.group(0)[:60],  # truncate for log safety
                "pattern": label,
                "position": match.start(),
            })
            # Keep any non-coordinate surrounding characters (keyword, brackets)
            full = match.group(0)
            coord_start = match.start(1) - match.start()
            coord_end = match.end(2) - match.start()
            return full[:coord_start] + PLACEHOLDER_GPS + full[coord_end:]

        # Labelled: "lat: X lon: Y"
        def _labelled_replace(m: re.Match) -> str:
            self._gps_count += 1
            self._details.append({
                "type": "GPS_COORDINATE", "pattern": "labelled",
                "match": m.group(0)[:60], "position": m.start(),
            })
            return re.sub(
                rf"{_LAT}{_COMPASS}[\s,;]+(?:lon(?:gitude)?|lng)\s*[:\-=]?\s*{_LON}{_COMPASS}",
                PLACEHOLDER_GPS,
                m.group(0),
                flags=re.IGNORECASE,
            )

        text = _GPS_LABELLED_PATTERN.sub(_labelled_replace, text)

        # Keyword-prefixed pair
        def _kw_replace(m: re.Match) -> str:
            self._gps_count += 1
            self._details.append({
                "type": "GPS_COORDINATE", "pattern": "keyword_prefix",
                "match": m.group(0)[:60], "position": m.start(),
            })
            # Replace only the coordinate pair, keep the keyword prefix
            replaced = re.sub(_GPS_PAIR, PLACEHOLDER_GPS, m.group(0), flags=re.IGNORECASE)
            return replaced

        text = _GPS_KEYWORD_PATTERN.sub(_kw_replace, text)

        # Bare high-precision pair (≥4 decimal places)
        def _bare_replace(m: re.Match) -> str:
            self._gps_count += 1
            self._details.append({
                "type": "GPS_COORDINATE", "pattern": "bare_decimal",
                "match": m.group(0)[:60], "position": m.start(),
            })
            return PLACEHOLDER_GPS

        text = _GPS_BARE_PATTERN.sub(_bare_replace, text)
        return text

    # ── Pass 2: Licence Plates ────────────────────────────────────────────────

    def _redact_plates(self, text: str) -> str:
        """Replace vehicle licence plate tokens with [PLATE_REDACTED]."""

        def _anchored_replace(m: re.Match) -> str:
            self._plate_count += 1
            self._details.append({
                "type": "LICENCE_PLATE", "pattern": "keyword_anchored",
                "match": m.group(0)[:40], "position": m.start(),
            })
            # Keep the keyword prefix, replace only the plate value (group 2)
            return m.group(0)[:m.start(2) - m.start()] + PLACEHOLDER_PLATE

        text = _PLATE_ANCHORED_PATTERN.sub(_anchored_replace, text)

        def _standalone_replace(m: re.Match) -> str:
            # Skip if already replaced by GPS or another pattern
            if PLACEHOLDER_GPS in m.group(0) or PLACEHOLDER_PLATE in m.group(0):
                return m.group(0)
            # Skip short tokens that could be abbreviations (e.g. "AV", "SD")
            if len(m.group(0).replace("-", "").replace(" ", "")) < 4:
                return m.group(0)
            self._plate_count += 1
            self._details.append({
                "type": "LICENCE_PLATE", "pattern": "standalone",
                "match": m.group(0)[:40], "position": m.start(),
            })
            return PLACEHOLDER_PLATE

        text = _PLATE_STANDALONE_PATTERN.sub(_standalone_replace, text)
        return text

    # ── Pass 3: Driver Names ──────────────────────────────────────────────────

    def _redact_driver_names(self, text: str) -> str:
        """Replace contextual driver name references with [DRIVER_REDACTED]."""

        def _name_replace(m: re.Match) -> str:
            self._driver_name_count += 1
            self._details.append({
                "type": "DRIVER_NAME", "pattern": "prefix_anchored",
                "match": m.group(0)[:60], "position": m.start(),
            })
            # Keep prefix keyword + separator, replace only the name (group 2)
            full = m.group(0)
            name_start = m.start(2) - m.start()
            return full[:name_start] + PLACEHOLDER_DRIVER

        text = _DRIVER_PATTERN.sub(_name_replace, text)
        return text

    # ── Public API ────────────────────────────────────────────────────────────

    def clean(self, raw_log_text: str) -> CleanerResult:
        """
        Run all three redaction passes on `raw_log_text`.

        Execution order:
          1. GPS coordinates   (prevent coordinate digits matching plate patterns)
          2. Licence plates    (prevent plate tokens matching name suffix patterns)
          3. Driver names      (last — most context-dependent)

        Args:
            raw_log_text: Raw AV disengagement log or field note text.

        Returns:
            CleanerResult with redacted text and redaction metadata.
        """
        if not raw_log_text or not raw_log_text.strip():
            return CleanerResult(original_text=raw_log_text, redacted_text=raw_log_text)

        # Reset counters for this invocation
        self._driver_name_count = 0
        self._plate_count = 0
        self._gps_count = 0
        self._details = []

        text = raw_log_text

        # Pass 1: GPS
        text = self._redact_gps(text)

        # Pass 2: Plates
        text = self._redact_plates(text)

        # Pass 3: Driver Names
        text = self._redact_driver_names(text)

        result = CleanerResult(
            original_text=raw_log_text,
            redacted_text=text,
            driver_name_count=self._driver_name_count,
            licence_plate_count=self._plate_count,
            gps_coordinate_count=self._gps_count,
            redaction_details=list(self._details),
        )

        logger.info(
            "enterprise_av_security_pii_cleaner complete",
            driver_names=result.driver_name_count,
            licence_plates=result.licence_plate_count,
            gps_coords=result.gps_coordinate_count,
            total=result.total_redactions,
        )

        return result


# ==============================================================================
# ADK FunctionTool Interface
# ==============================================================================

# Module-level singleton — instantiated once, thread-safe for read-only regex ops
_cleaner = EnterpriseAVSecurityPIICleaner()


def clean_pii(raw_log_text: str) -> dict:
    """
    Sanitise raw AV disengagement log text by redacting driver names,
    vehicle licence plates, and decimal GPS coordinates using deterministic
    regular expression patterns.

    This tool must be invoked on all raw log text BEFORE any LLM processing.
    It operates without model inference — deterministic, fast, and auditable.

    Redaction placeholders:
      - Driver names    → [DRIVER_REDACTED]
      - Licence plates  → [PLATE_REDACTED]
      - GPS coordinates → [GPS_REDACTED]

    Args:
        raw_log_text: Raw text from the AV log ingestion pipeline. May contain
                      safety driver names, vehicle registration plates, and/or
                      decimal GPS coordinate pairs mixed with engineering notes.

    Returns:
        A dictionary with:
          - redacted_text (str): Sanitised text safe for LLM processing.
          - pii_found (bool): True if any PII was detected.
          - redaction_summary (dict): Count per category and total.
          - original_char_count (int): Input character count.
          - redacted_char_count (int): Output character count.
          - redaction_details (list): Per-entity metadata (type, pattern, position).
    """
    result = _cleaner.clean(raw_log_text)

    return {
        "redacted_text": result.redacted_text,
        "pii_found": result.pii_found,
        "redaction_summary": {
            "driver_names": result.driver_name_count,
            "licence_plates": result.licence_plate_count,
            "gps_coordinates": result.gps_coordinate_count,
            "total": result.total_redactions,
        },
        "original_char_count": len(result.original_text),
        "redacted_char_count": len(result.redacted_text),
        "redaction_details": result.redaction_details,
    }


# ==============================================================================
# CLI Quick-Test
# ==============================================================================

if __name__ == "__main__":
    _SAMPLE = """
    DISENGAGEMENT REPORT — 2026-06-15T14:32:00Z
    Safety Driver: Mr. Jordan Whitfield
    Unit plate: 7XYZ890
    Fleet ID: CA 3ABC021

    Vehicle was operating in autonomous mode on Mission Street.
    GPS position at disengagement: 37.774929, -122.419418
    Secondary waypoint logged at lat: 37.7752 lon: -122.4181

    Operator Priya Subramaniam noted that forward camera occluded by sun glare.
    Driver resumed manual control at coords(37.774900, -122.419400).
    Tech: Sam O'Brien confirmed sensor recalibration at depot post-incident.
    Submitted by: Engineer Lisa Fernandez-Cruz — Zone 7 ops.

    Notes: AV-FLEET-402 running v4.2.1-beta. Wet road surface observed.
    No structural damage. Plate of following vehicle: AB12 CDE (witness).
    """

    import json
    output = clean_pii(_SAMPLE)
    print("=" * 60)
    print("REDACTED TEXT:")
    print(output["redacted_text"])
    print("=" * 60)
    print("SUMMARY:", json.dumps(output["redaction_summary"], indent=2))
    print("DETAILS:")
    for d in output["redaction_details"]:
        print(f"  [{d['type']}] pattern={d['pattern']} pos={d['position']}")
