"""
the individual artists an event names, from its free-text title and artists fields, so each
act on a bill can be looked up on its own (see match_spotify_artists):

    event_artist_names(event)  # ["SHEBAD", "Psymon Spine", "A Halloween Surprise"]

"&" and "and" are never separators: they're inside too many band names ("Mumford & Sons").
a duo billed together ("Connor Garvey & Ben Cosgrove") is split only when spotify has no
artist by the whole name: see name_parts.
"""

import re

from core.artist_matching import normalize

SEPARATOR_RE = re.compile(
    r"\s*[,;]\s*|\s*//\s*|\s+/\s+|\s+\+\s+|\s+x\s+|\s+w/\s*|\s+with\s+|\s+(?:feat\.?|ft\.?|featuring)\s+",
    re.IGNORECASE,
)
# "State Theatre Presents: The Ballroom Thieves", "An evening with Lake Street Dive"
TITLE_PREFIX_RE = re.compile(r"^(?:.*?\bpresents\b\s*:?|an evening with)\s+", re.IGNORECASE)
# titles that name a kind of night rather than its acts
TITLE_STOPWORDS_RE = re.compile(
    r"\b(?:tribute|party|night|festival|open mic|karaoke)\b", re.IGNORECASE
)
# "Còig - early show", "Elderbrook - Heart On A Wire Tour", "2hollis: The Pirouette Tour":
# after a spaced dash or a colon comes the show's name, not more of the artist's.
# a dash needs a space before it, so "GA-20" and "Jay-Z" stay whole
SUBTITLE_RE = re.compile(r"\s*:\s+|\s+[-–—]\s*|\s*[–—]\s+")
# "Connor Garvey & Ben Cosgrove": two acts billed together
DUO_RE = re.compile(r"\s+(?:&|and)\s+", re.IGNORECASE)
# "Chris Cote and his Band of These Guys": a leader and their backing band
BACKING_BAND_RE = re.compile(r"^(?:his|her|their)\b", re.IGNORECASE)
# words that name an occasion rather than an artist: "Built to Spill Fall 2026 Tour",
# "BUFFALO TOM 3rd Annual charity concert". compared normalized
OCCASION_WORDS = {
    "tour", "annual", "anniversary", "concert", "show", "celebration", "residency", "release",
    "holiday", "christmas", "benefit", "charity", "reunion", "farewell", "birthday", "edition",
}
# "Rhiannon Hurst (21+)", "49th & Main (DJ Set)": notes after a name, not part of it.
# "with Jacyn Tremblay": a bill that starts "with ..."
TRAILING_NOTE_RE = re.compile(
    r"\s*\(\s*(?:\d+\s*\+|all ages|dj set|live set|live|acoustic|solo|full band)\s*\)\s*$",
    re.IGNORECASE,
)
LEADING_WITH_RE = re.compile(r"^with\s+", re.IGNORECASE)
# what bills say in place of a name, compared normalized
PLACEHOLDERS = {"tba", "tbd", "special guest", "special guests", "and more", "organization", "dj"}


def clean_name(name):
    name, before = SUBTITLE_RE.split(name.strip(), maxsplit=1)[0], None
    # notes can stack: "Glass Halo (DJ Set) (21+)"
    while name != before:
        before, name = name, TRAILING_NOTE_RE.sub("", name)
    return LEADING_WITH_RE.sub("", name).strip()


def split_names(text):
    # str(): a title or artists value needn't be a string until the event is saved
    names = (clean_name(name) for name in SEPARATOR_RE.split(str(text or "")))
    return [name for name in names if name]


def title_names(title):
    """
    the title's names. a kind of night ("tribute", "party"...) rules a name out only where
    it isn't in the dropped show name: "Damn the Torpedoes - a Tribute To Tom Petty" names
    the band, but "Dirty Deeds AC/DC Tribute" names no one
    """
    if not title:
        return []
    names = split_names(TITLE_PREFIX_RE.sub("", str(title).strip()))
    return [name for name in names if not TITLE_STOPWORDS_RE.search(name)]


def name_parts(name):
    """
    the acts in a duo billing like "Connor Garvey & Ben Cosgrove", or [] when it isn't one.
    each part must have two words or more, so "Mumford & Sons" and "Simon & Garfunkel" are
    never split; and they're searched only when the whole name isn't an artist
    """
    parts = [part.strip() for part in DUO_RE.split(name)]
    # a backing band isn't searched on its own: "Chris Cote and his Band of These Guys"
    parts = parts[:1] + [part for part in parts[1:] if not BACKING_BAND_RE.match(part)]
    if len(DUO_RE.split(name)) < 2 or any(len(normalize(part).split()) < 2 for part in parts):
        return []
    return parts


def occasion_prefix(key, artist_keys):
    """
    the longest of artist_keys that starts this normalized name, when the rest of it names
    an occasion: "built to spill fall 2026 tour" -> "built to spill". or None
    """
    words = key.split()
    for end in range(len(words) - 1, 0, -1):
        prefix, rest = " ".join(words[:end]), words[end:]
        if prefix in artist_keys and OCCASION_WORDS & set(rest):
            return prefix
    return None


def is_placeholder(name):
    key = normalize(name)
    return len(key) <= 1 or key in PLACEHOLDERS


def event_artist_names(event):
    """the event's artist names, title's first, in order and without repeats"""
    if not event.is_music_kind:
        return []
    names, seen = [], set()
    for name in title_names(event.title) + split_names(event.artists):
        key = normalize(name)
        if is_placeholder(name) or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names
