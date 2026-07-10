"""Regex-based scrubbing applied to every string value in a tool's response,
including fields that survived the per-tool allowlist. This is
defense-in-depth: it catches secrets/PII that leak into otherwise-legitimate
fields (e.g. an error message that happens to echo an internal hostname).

Matches are replaced with a typed placeholder so redaction is visible to the
reader rather than silently altering the text.
"""

from __future__ import annotations

import re

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "IPV4_ADDRESS",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    ),
    ("IPV6_ADDRESS", re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b")),
    ("AWS_ARN", re.compile(r"arn:aws:[a-zA-Z0-9\-]+:[a-zA-Z0-9\-]*:\d{0,12}:[^\s\"']+")),
    ("EMAIL_ADDRESS", re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b")),
    # Harness API keys / PAT-shaped tokens (pat.<account>.<...>, sat.<...>).
    ("HARNESS_TOKEN", re.compile(r"\b(?:pat|sat|nat)\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9_\-.=]{20,}\b")),
    # Generic long high-entropy base64/hex-ish token, conservative min length.
    ("JWT_LIKE", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "PRIVATE_HOSTNAME",
        re.compile(
            r"\b(?:ip-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}\.[\w.-]*internal|"
            r"[\w-]+\.(?:internal|corp|local))\b"
        ),
    ),
)


def scrub_string(value: str) -> tuple[str, list[str]]:
    """Return (cleaned_value, kinds_redacted)."""
    hits: list[str] = []
    cleaned = value
    for kind, pattern in _PATTERNS:
        if pattern.search(cleaned):
            hits.append(kind)
            cleaned = pattern.sub(f"[REDACTED:{kind}]", cleaned)
    return cleaned, hits
