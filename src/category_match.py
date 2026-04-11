"""Align LLM-returned categories to configured keywords."""

from difflib import get_close_matches
from typing import List


def resolve_category(raw: str, keywords: List[str]) -> str:
    """
    Map a model-produced category to a canonical entry in config.keywords.

    Tries in order: exact match, case-insensitive match, fuzzy match,
    substring inclusion for longer keywords.
    """
    text = (raw or "").strip()
    if not text:
        return ""

    for kw in keywords:
        if text == kw:
            return kw

    lower = text.lower()
    for kw in keywords:
        if lower == kw.lower():
            return kw

    close = get_close_matches(text, keywords, n=1, cutoff=0.72)
    if close:
        return close[0]

    # Prefer longer keywords first to reduce false matches
    for kw in sorted(keywords, key=len, reverse=True):
        if len(kw) < 8:
            continue
        kl = kw.lower()
        if lower in kl or kl in lower:
            return kw

    return ""
