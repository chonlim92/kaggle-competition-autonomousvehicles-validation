"""
src/skills/pii_redactor/redactor.py

Core PII detection and redaction engine.

Uses Microsoft Presidio (presidio-analyzer + presidio-anonymizer) backed by a
spaCy NER model for entity recognition. Configured through `AgentConfig` so
the redaction mode and placeholder are environment-driven.

Supported Entity Types (default set)
-------------------------------------
- PERSON              — human names
- EMAIL_ADDRESS       — email addresses
- PHONE_NUMBER        — phone numbers
- LOCATION            — street addresses / GPS coordinates
- US_DRIVER_LICENSE   — US driver's licence numbers
- US_SSN              — Social Security Numbers
- CREDIT_CARD         — credit card numbers
- IP_ADDRESS          — IP addresses
- URL                 — URLs
- DATE_TIME           — dates / timestamps (context-dependent)
- NRP                 — nationalities, religions, political groups
- VEHICLE_ID          — custom recognizer for VINs (see below)
- LICENSE_PLATE       — custom recognizer for licence plates (see below)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Optional Presidio import — graceful degradation when not installed
# ---------------------------------------------------------------------------
try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False
    logger.warning(
        "presidio-analyzer / presidio-anonymizer not installed. "
        "Falling back to regex-only PII redaction. "
        "Run `pip install presidio-analyzer presidio-anonymizer` for full coverage."
    )


# ---------------------------------------------------------------------------
# Custom Recognizers
# ---------------------------------------------------------------------------

# Vehicle Identification Number (VIN): 17 alphanumeric chars (no I, O, Q)
_VIN_PATTERN = Pattern(
    name="VIN_pattern",
    regex=r"\b[A-HJ-NPR-Z0-9]{17}\b",
    score=0.85,
)

# Generic licence plate (EU/US style — extend as needed)
_PLATE_PATTERN = Pattern(
    name="licence_plate_pattern",
    regex=r"\b[A-Z]{1,3}[- ]?\d{1,4}[- ]?[A-Z]{0,3}\b",
    score=0.6,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class RedactionResult:
    """Result returned by the PIIRedactor."""

    original_text: str
    redacted_text: str
    detected_entities: List[dict] = field(default_factory=list)
    pii_found: bool = False

    def __post_init__(self) -> None:
        self.pii_found = bool(self.detected_entities)


# ---------------------------------------------------------------------------
# PIIRedactor class
# ---------------------------------------------------------------------------

class PIIRedactor:
    """
    Detects and redacts PII from text strings.

    Parameters
    ----------
    mode : str
        One of 'mask' | 'redact' | 'tokenize'.
        - mask     : replace with `placeholder` string
        - redact   : replace with '<ENTITY_TYPE>' tag
        - tokenize : replace with a deterministic token (hash-based)
    placeholder : str
        The string used when mode == 'mask'. Default: '[REDACTED]'
    entity_types : list[str] | None
        Specific Presidio entity types to detect. None = all supported.
    language : str
        Language code for the Presidio NLP engine. Default: 'en'.
    """

    DEFAULT_ENTITIES = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "LOCATION",
        "US_DRIVER_LICENSE",
        "US_SSN",
        "CREDIT_CARD",
        "IP_ADDRESS",
        "URL",
        "VEHICLE_ID",
        "LICENSE_PLATE",
    ]

    def __init__(
        self,
        mode: str = "mask",
        placeholder: str = "[REDACTED]",
        entity_types: Optional[List[str]] = None,
        language: str = "en",
    ) -> None:
        self.mode = mode
        self.placeholder = placeholder
        self.entity_types = entity_types or self.DEFAULT_ENTITIES
        self.language = language

        if _PRESIDIO_AVAILABLE:
            self._analyzer = self._build_analyzer()
            self._anonymizer = AnonymizerEngine()
        else:
            self._analyzer = None
            self._anonymizer = None

    # ── Presidio setup ───────────────────────────────────────────────────────

    def _build_analyzer(self) -> "AnalyzerEngine":  # type: ignore[return]
        """Construct AnalyzerEngine with custom AV-domain recognizers."""
        analyzer = AnalyzerEngine()

        vin_recognizer = PatternRecognizer(
            supported_entity="VEHICLE_ID",
            patterns=[_VIN_PATTERN],
        )
        plate_recognizer = PatternRecognizer(
            supported_entity="LICENSE_PLATE",
            patterns=[_PLATE_PATTERN],
        )
        analyzer.registry.add_recognizer(vin_recognizer)
        analyzer.registry.add_recognizer(plate_recognizer)
        return analyzer

    # ── Regex fallback ───────────────────────────────────────────────────────

    _REGEX_PATTERNS: dict[str, str] = {
        "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "PHONE": r"\+?[\d\s\-().]{7,15}",
        "VIN": r"\b[A-HJ-NPR-Z0-9]{17}\b",
        "IP": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "URL": r"https?://[^\s]+",
    }

    def _regex_redact(self, text: str) -> RedactionResult:
        """Fallback regex-based redaction when Presidio is unavailable."""
        redacted = text
        entities: list[dict] = []
        for entity_type, pattern in self._REGEX_PATTERNS.items():
            matches = list(re.finditer(pattern, redacted))
            if matches:
                entities.append({"type": entity_type, "count": len(matches)})
            redacted = re.sub(pattern, self.placeholder, redacted)

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            detected_entities=entities,
        )

    # ── Operator config for Presidio anonymizer ───────────────────────────────

    def _build_operator_config(self, entity_type: str) -> "OperatorConfig":  # type: ignore[return]
        """Map redaction mode to Presidio OperatorConfig."""
        if self.mode == "redact":
            return OperatorConfig("replace", {"new_value": f"<{entity_type}>"})
        elif self.mode == "tokenize":
            return OperatorConfig("hash", {"hash_type": "sha256"})
        else:  # mask (default)
            return OperatorConfig("replace", {"new_value": self.placeholder})

    # ── Public API ───────────────────────────────────────────────────────────

    def redact(self, text: str) -> RedactionResult:
        """
        Detect and redact PII in `text`.

        Returns a `RedactionResult` with the cleaned text and entity metadata.
        """
        if not text or not text.strip():
            return RedactionResult(original_text=text, redacted_text=text)

        if not _PRESIDIO_AVAILABLE or self._analyzer is None:
            logger.debug("Using regex fallback redaction")
            return self._regex_redact(text)

        try:
            results = self._analyzer.analyze(
                text=text,
                entities=self.entity_types,
                language=self.language,
            )

            operator_config = {
                entity.entity_type: self._build_operator_config(entity.entity_type)
                for entity in results
            }

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=operator_config,
            )

            detected = [
                {
                    "type": r.entity_type,
                    "start": r.start,
                    "end": r.end,
                    "score": round(r.score, 3),
                }
                for r in results
            ]

            logger.info(
                "PII redaction complete",
                entity_count=len(detected),
                mode=self.mode,
            )

            return RedactionResult(
                original_text=text,
                redacted_text=anonymized.text,
                detected_entities=detected,
            )

        except Exception as exc:
            logger.error("PII redaction failed", error=str(exc))
            # Safe fallback: return original text unmodified rather than crash
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                detected_entities=[{"error": str(exc)}],
            )
