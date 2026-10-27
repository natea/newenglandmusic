"""
comparing artist names across sources (our events, spotify): two spellings of a band's
name should compare equal when they differ only in case, accents, punctuation, "&" for
"and" or a leading "the".
"""

import re
import unicodedata


def normalize(name):
    """lowercase words without accents or punctuation, "&" as "and", no leading "the" """
    name = unicodedata.normalize("NFKD", name or "")
    name = "".join(char for char in name if not unicodedata.combining(char))
    name = name.lower().replace("&", " and ")
    # apostrophes join words ("haven's" -> "havens") rather than splitting them
    name = re.sub(r"['’]", "", name)
    name = re.sub(r"[^\w\s]|_", " ", name)
    name = " ".join(name.split())
    return re.sub(r"^the ", "", name)
