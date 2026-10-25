"""
deciding whether a listing on another service (google places, ticketmaster) is the same
venue as one of ours: by name, and by distance.
"""

import math
import re

# words that venues' names often gain or lose between listings
NAME_NOISE_RE = re.compile(
    r"\b(the|music hall|hall|club|theatre|theater|live|and|at)\b|presented by .*$"
)


def normalize_name(name):
    """lowercase words, without punctuation or words like "the" and "club" """
    name = name.lower().replace("&", " and ")
    name = re.sub(r"[^\w\s]", " ", name)
    words = NAME_NOISE_RE.sub(" ", " ".join(name.split()))
    return " ".join(words.split()) or " ".join(name.split())


def names_match(a, b):
    """equal, or one's words appear in a row in the other's"""
    a, b = normalize_name(a), normalize_name(b)
    return bool(a and b) and (f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))
