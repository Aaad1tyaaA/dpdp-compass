"""Redact personal data from user input before it is processed, stored or logged."""
from __future__ import annotations

import re

# ponytail: regex-only. Catches structured identifiers and introduced names ("my name is ...", "Mr ...");
# free-standing names in running text need an NER model (add one here if inputs contain them).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("AADHAAR", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("PHONE", re.compile(r"(?<![\d\w])(?:\+?91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)|(?<![\d\w])\+\d{1,3}[ -]?\d{6,12}(?!\d)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("PASSPORT", re.compile(r"\b[A-Z][1-9]\d{6}\b")),
    ("NAME", re.compile(r"(?:(?<=\bmy name is )|(?<=\bMy name is )|(?<=\bName: )|(?<=\bname: ))[A-Z][a-z]+(?: [A-Z][a-z]+){0,2}")),
    ("NAME", re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Shri|Smt)\.? [A-Z][a-z]+(?: [A-Z][a-z]+){0,2}")),
]


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Return (redacted text, count per category). Placeholders look like [EMAIL], [PHONE]."""
    counts: dict[str, int] = {}
    for label, pattern in _PATTERNS:
        text, n = pattern.subn(f"[{label}]", text)
        if n:
            counts[label] = counts.get(label, 0) + n
    return text, counts
