"""
deciding whether a listing on another service (google places, ticketmaster) is the same
venue as one of ours: by name, and by distance.
"""

import math
import re
import unicodedata

# words that venues' names often gain or lose between listings. the review reasons
# (2026-10-29) showed 172 of 176 reviews failing on the name alone, mostly over these and
# apostrophes ("Fast Eddie's Billiards" vs "Fast Eddies Billiards Cafe")
NAME_NOISE_RE = re.compile(
    r"\b(the|music hall|hall|club|theatre|theater|live|and|at|cafe|pub|bar|restaurant|grill"
    r"|tavern|lounge|bistro|brewery|taproom)\b|presented by .*$"
)
ABBREVIATIONS = {"st": "street", "ave": "avenue", "rd": "road"}
ABBREVIATION_RE = re.compile(r"\b(st|ave|rd)\b")


def cleaned(name):
    """
    lowercase words, without accents, punctuation or a trailing "(...)"; apostrophes join
    their words ("eddie's" -> "eddies") and st/ave/rd are spelled out
    """
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().replace("&", " and ")
    name = re.sub(r"['’]", "", name)
    name = re.sub(r"(?<=\S)\s*\([^()]*\)\s*$", "", name)
    name = re.sub(r"[^\w\s]", " ", name)
    return ABBREVIATION_RE.sub(lambda m: ABBREVIATIONS[m.group(1)], " ".join(name.split()))


def only_noise_words(cleaned_name):
    return not NAME_NOISE_RE.sub(" ", cleaned_name).strip()


def normalize_name(name):
    """the cleaned name without words like "the" and "club", or all of it if that's all it is"""
    name = cleaned(name)
    return " ".join(NAME_NOISE_RE.sub(" ", name).split()) or name


def spelling_variants(name):
    """the name, plus its other spelling of theater/theatre: ticketmaster's search matches
    words literally, so "The State Theater" doesn't find "State Theatre"."""
    swapped = re.sub(
        r"\b(theat)(er|re)\b",
        lambda m: m.group(1) + ("re" if m.group(2).lower() == "er" else "er"),
        name,
        flags=re.IGNORECASE,
    )
    return [name] if swapped == name else [name, swapped]


def names_match(a, b, place_words=""):
    """
    equal, or one's words appear in a row in the other's. a name of only noise words must be
    equal, ignoring "the" and any words of `place_words` (the venue's town and
    state): "The Music Hall" matches "The Music Hall, Portsmouth, NH" but not "The Music Hall
    Lounge", a separate venue (2026-10-29)
    """
    full_a, full_b = cleaned(a), cleaned(b)
    a, b = normalize_name(a), normalize_name(b)
    if not (a and b):
        return False
    if only_noise_words(full_a) or only_noise_words(full_b):
        ignored = {"the", *normalize_name(place_words).split()}
        return [w for w in full_a.split() if w not in ignored] == [w for w in full_b.split() if w not in ignored]
    return f" {a} " in f" {b} " or f" {b} " in f" {a} "


def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))
