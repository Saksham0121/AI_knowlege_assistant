"""
Text cleaner: removes noise, normalizes whitespace and unicode.
"""
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Apply all cleaning steps to raw extracted text."""
    text = _normalize_unicode(text)
    text = _remove_control_chars(text)
    text = _remove_excessive_whitespace(text)
    text = _remove_repeated_chars(text)
    return text.strip()


def _normalize_unicode(text: str) -> str:
    """Normalize unicode to NFC form and replace common ligatures."""
    text = unicodedata.normalize("NFC", text)
    replacements = {
        "\ufb01": "fi", "\ufb02": "fl", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u00a0": " ", "\u2022": "*",
    }
    for orig, replacement in replacements.items():
        text = text.replace(orig, replacement)
    return text


def _remove_control_chars(text: str) -> str:
    """Remove non-printable control characters except newlines and tabs."""
    return "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cc", "Cf") or ch in ("\n", "\t", "\r")
    )


def _remove_excessive_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs to single space; collapse 3+ newlines to 2."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _remove_repeated_chars(text: str) -> str:
    """Remove lines that are only repeated special characters (page separators, etc.)."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are only dashes, dots, underscores, or stars
        if re.fullmatch(r"[-_=.*#|]{3,}", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
