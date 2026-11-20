"""Text Normalization Module for Patent Documents (PAT-0204).

Provides pure, deterministic text normalization functions that preserve
technical terms, symbols, patent numbers, and paragraph structure without
altering source semantics.
"""

import html
import re
import unicodedata


def clean_html_tags(text: str) -> str:
    """Strip HTML/XML tags while preserving meaningful whitespace boundaries."""
    if not text:
        return ""
    # Replace block level tags with newlines
    text = re.sub(r'</?(?:p|div|br|section|heading|h[1-6]|dd|dt|tr)[^>]*>', '\n', text, flags=re.I)
    # Strip any remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    return text


def decode_html_entities(text: str) -> str:
    """Unescape HTML and XML numeric / named character references."""
    if not text:
        return ""
    return html.unescape(text)


def normalize_unicode(text: str) -> str:
    """
    Normalize unicode characters into standard NFC form while mapping
    special punctuation (smart quotes, em/en dashes, non-breaking spaces)
    to clean equivalents without destroying technical symbols.
    """
    if not text:
        return ""
    # Unicode canonical normalization
    text = unicodedata.normalize("NFC", text)

    # Specific replacements
    replacements = {
        "\u00a0": " ",  # Non-breaking space
        "\u200b": "",   # Zero-width space
        "\u201c": '"',  # Left double quotation
        "\u201d": '"',  # Right double quotation
        "\u2018": "'",  # Left single quotation
        "\u2019": "'",  # Right single quotation
        "\u2014": " - ", # Em dash
        "\u2013": "-",  # En dash
        "\u2026": "...", # Ellipsis
        "\r\n": "\n",   # Windows line endings
        "\r": "\n",     # Classic Mac line endings
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def normalize_whitespace(text: str, preserve_paragraphs: bool = True) -> str:
    """
    Collapse excessive horizontal whitespace.
    If preserve_paragraphs is True, maintains double newlines separating paragraphs.
    """
    if not text:
        return ""

    if preserve_paragraphs:
        # Split on double or multiple newlines
        paragraphs = re.split(r'\n\s*\n+', text)
        cleaned_paras = []
        for p in paragraphs:
            # Collapse internal whitespace within paragraph
            p_clean = " ".join(p.split())
            if p_clean:
                cleaned_paras.append(p_clean)
        return "\n\n".join(cleaned_paras)
    else:
        return " ".join(text.split())


def normalize_patent_text(text: str, preserve_paragraphs: bool = True) -> str:
    """
    Full normalization pipeline for patent text bodies.
    Safe on technical terms (e.g. 'RLC circuit', 'pF', '5V', 'US11457576B2').
    """
    if not text:
        return ""
    cleaned = clean_html_tags(text)
    decoded = decode_html_entities(cleaned)
    unicoded = normalize_unicode(decoded)
    normalized = normalize_whitespace(unicoded, preserve_paragraphs=preserve_paragraphs)
    return normalized

