"""Patent Tokenizer and Query Pre-processing Module (PAT-0301).

Implements deterministic, technical-term-preserving tokenization for English patent
documents and user search queries using standard library regular expressions.
"""

import re
from typing import Optional
import unicodedata

# Minimal, documented English stopword set.
# Excludes general discourse words while strictly preserving technical terms, units, and identifiers.
ENGLISH_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but",
    "by", "did", "do", "does", "for", "from", "had", "has", "have", "in",
    "is", "not", "of", "on", "or", "that", "the", "these", "this", "those",
    "to", "was", "were", "with",
}

# Regex pattern matching:
# 1. CPC/IPC codes or compound identifiers: e.g. A01G25/16, G01N33/24, US11457576B2
# 2. Hyphenated technical words: e.g. in-ground, low-power, multi-zone
# 3. Alphanumeric terms with units: e.g. 5v, 100pf, 2.4ghz
# 4. Unicode-aware word characters: prevents spurious splitting of non-ASCII terms (e.g. 'sensörü' -> 'sensörü', avoiding rogue 'r')
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[/\-_][^\W_]+)*", re.UNICODE)


def normalize_query_text(text: Optional[str]) -> str:
    """Normalize unicode and case cleanly without altering technical strings."""
    if not text or not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    return text.strip().lower()


def tokenize(text: Optional[str], remove_stopwords: bool = True) -> list[str]:
    """
    Tokenize input patent or query text into a list of normalized string tokens.
    Deterministic, case-folded, and preserves technical units, CPC codes, and hyphenated terms.
    """
    if not text or not isinstance(text, str):
        return []

    norm_text = normalize_query_text(text)
    if not norm_text:
        return []

    raw_matches = TOKEN_PATTERN.findall(norm_text)
    tokens: list[str] = []

    for match in raw_matches:
        # Strip trailing punctuation if any caught
        token = match.strip("/-_.")
        if not token:
            continue

        if remove_stopwords and token in ENGLISH_STOPWORDS:
            continue

        tokens.append(token)

    return tokens

