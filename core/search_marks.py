"""
what was searched, marked in what search found (the results page and, in javascript,
core/static/core/js/search-suggest.js, which does the same). names match ignoring case,
accents and punctuation (core.artist_matching.normalize), so the mark is found on the
name folded the same way and then put back on its own characters: "bel" marks "Bé" in
"Béla Fleck", "o'b" marks "O'B" in "O'Brien's".
"""

import unicodedata

from django.utils.html import escape
from django.utils.safestring import mark_safe


def fold(char):
    """a character as matching sees it: lowercase, without accents, and only letters or digits"""
    plain = "".join(c for c in unicodedata.normalize("NFKD", char) if not unicodedata.combining(c))
    return "".join(c for c in plain.lower() if c.isalnum())


def match_span(text, query):
    """(start, end) of the query in text, as characters of text, or None"""
    wanted = "".join(fold(c) for c in query or "")
    if not wanted:
        return None
    folded, origin = [], []
    for i, char in enumerate(text or ""):
        for c in fold(char):
            folded.append(c)
            origin.append(i)
    at = "".join(folded).find(wanted)
    if at < 0:
        return None
    return origin[at], origin[at + len(wanted) - 1] + 1


def mark_match(text, query):
    """text, escaped, with the part matching the query in <mark>"""
    span = match_span(text, query)
    if not span:
        return escape(text)
    start, end = span
    return mark_safe(f"{escape(text[:start])}<mark>{escape(text[start:end])}</mark>{escape(text[end:])}")
