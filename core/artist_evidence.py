"""
the rules resolve_artists_with_lastfm uses to decide whether the act a last.fm page and
musicbrainz name is the one playing our venues (see openspec/specs/lastfm-artist-evidence):
- local: musicbrainz's area for it is in a state the site covers, going by musicbrainz's own
  "part of" links rather than the town's name, or its last.fm bio names a covered state and
  doesn't say several acts share the name;
- dominant: last.fm counts at least DOMINANT_LISTENERS listeners, and its bio doesn't say
  several acts share the name. a famous act's namesakes are almost always tiny, and it's
  them that make the name ambiguous on spotify.
"""

import re

DOMINANT_LISTENERS = 100_000

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# last.fm's own notes on a page several acts share: "There are at least two bands using the
# name...", "There are several bands called...", "There are 2 groups called..."
SHARED_NOTE_RE = re.compile(
    r"\bthere (?:are|were) (?:at least |over |more than )?(?:two|three|four|five|six|several|many|multiple|various|\d+)\b",
    re.IGNORECASE,
)
# or a numbered list of acts: "1) ... 2) ..." or "1. ... 2. ..."
NUMBERED_ACTS_RE = re.compile(r"(?:^|\s)1[).]\s.*?(?:^|\s)2[).]\s", re.DOTALL)


def covered_places():
    """{"states": {code: full name}, "towns": {town}} where the site has venues"""
    from core.models import Venue

    rows = Venue.objects.exclude(state="").values_list("state", "city_town").distinct()
    states, towns = {}, set()
    for state, town in rows:
        code = state.upper()
        if code in STATE_NAMES:
            states[code] = STATE_NAMES[code]
        if town and town.strip():
            towns.add(town.strip())
    return {"states": states, "towns": towns}


def whole_words(phrase):
    return re.compile(rf"(?<![\w]){re.escape(phrase)}(?![\w])", re.IGNORECASE)


def names_covered_place(text, places):
    """
    whether a bio names a covered state: in full ("Western Massachusetts"), or after a town
    ("Worcester, MA"). a town on its own doesn't count, since many are also surnames or
    words ("Johnson", "Lincoln", "Warren": a bio naming a person matched Johnson, VT)
    """
    text = text or ""
    if not text.strip():
        return False
    for code, name in places["states"].items():
        if whole_words(name).search(text):
            return True
        if re.search(rf"\b[A-Z][\w.' -]*, {code}\b", text):
            return True
    return False


def is_covered_subdivision(code, places):
    """whether an iso 3166-2 code ("US-MA") is a state where the site has venues"""
    country, _, state = (code or "").partition("-")
    return country == "US" and state in places["states"]


def shares_name(bio):
    """whether last.fm's bio says several acts share the page's name"""
    bio = bio or ""
    return bool(SHARED_NOTE_RE.search(bio) or NUMBERED_ACTS_RE.search(bio))


def is_dominant(listeners, bio):
    return (listeners or 0) >= DOMINANT_LISTENERS and not shares_name(bio)
