"""PII scrubber — regex-based redaction of sensitive data fields."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class ScrubResult:
    """Result of a scrub operation."""

    text: str
    flags: list[str] = field(default_factory=list)


# Compiled patterns for performance
_PATTERNS: dict[str, re.Pattern[str]] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{3,4}\b"),
    "EMAIL": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    ),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ \-]?){13,16}\b"),
    "PHONE": re.compile(
        r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
    "IP_ADDRESS": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def scrub_text(text: str) -> ScrubResult:
    """Scrub all known PII patterns from a string.

    Args:
        text: Raw input text that may contain PII.

    Returns:
        ScrubResult with redacted text and list of detected PII types.
    """
    flags: list[str] = []
    for pii_type, pattern in _PATTERNS.items():
        if pattern.search(text):
            flags.append(pii_type)
            text = pattern.sub(f"[REDACTED:{pii_type}]", text)
    return ScrubResult(text=text, flags=flags)


def scrub_dict(data: dict) -> tuple[dict, list[str]]:  # type: ignore[type-arg]
    """Recursively scrub all string values in a dict.

    Args:
        data: Dictionary possibly containing PII in nested string values.

    Returns:
        Tuple of (scrubbed_dict, aggregated_flags).
    """
    all_flags: list[str] = []

    def _walk(obj: object) -> object:
        if isinstance(obj, str):
            result = scrub_text(obj)
            all_flags.extend(result.flags)
            return result.text
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        return obj

    scrubbed = _walk(data)
    return scrubbed, list(set(all_flags))  # type: ignore[return-value]


def scrub_json_str(raw: str) -> tuple[str, list[str]]:
    """Parse JSON string, scrub it, and serialise back.

    Args:
        raw: JSON-encoded string.

    Returns:
        Tuple of (scrubbed JSON string, detected PII flag types).
    """
    try:
        data = json.loads(raw)
        scrubbed, flags = scrub_dict(data)
        return json.dumps(scrubbed, sort_keys=True), flags
    except json.JSONDecodeError:
        result = scrub_text(raw)
        return result.text, result.flags
