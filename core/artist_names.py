"""
the individual artists an event names, from its free-text title and artists fields, so each
act on a bill can be looked up on its own (see match_spotify_artists):

    event_artist_names(event)  # ["SHEBAD", "Psymon Spine", "Shadow Show"]

"&" and "and" are never separators: they're inside too many band names ("Mumford & Sons").
a duo billed together ("Connor Garvey & Ben Cosgrove") is split only when spotify has no
artist by the whole name: see name_parts.
"""

import re

from core.artist_matching import normalize

# a comma then "&" or "and" ends a list ("DÀN, & Aydan Hill"); "&" alone is inside names.
# a slash needs a space on one side ("Sue Foley/ GA-20"), so "AC/DC" stays whole
SEPARATOR_RE = re.compile(
    r"\s*,\s*(?:&|and)\s+|\s*[,;]\s*|\s*//\s*|\s+/\s*|\s*/\s+|\s+\+\s+|\s+x\s+|\s+w\s*/\s*|\s+with\s+|\s+(?:feat\.?|ft\.?|featuring)\s+",
    re.IGNORECASE,
)
# "State Theatre Presents: The Ballroom Thieves", "An evening with Lake Street Dive",
# "Evening With - John Splithoff"
TITLE_PREFIX_RE = re.compile(r"^(?:.*?\bpresents\b\s*:?|(?:an\s+)?evening\s+with(?:\s*[-–—:])?)\s+", re.IGNORECASE)
# titles that name a kind of night rather than its acts. the second line came from the
# titles' names on 2026-10-29 ("Irish Session", "Jazz Jam", "Live Music at SAL's Birch Bar",
# "Jazz Wednesdays", "WXPN Welcomes", "Porchfest", "A Celtic Christmas", "FREE", "Live Jazz"). "tour"
# isn't one: "Built to Spill Fall 2026 Tour" names its act (see occasion_prefix)
TITLE_STOPWORDS_RE = re.compile(
    r"\b(?:tribute|party|night|festival|open mic|karaoke"
    r"|jams?|sessions?|brunch|live music|open stage|series|showcase|christmas|halloween|intimate evening"
    r"|welcomes|battle of the bands|music of|songs of|(?:mon|tues|wednes|thurs|fri|satur|sun)days"
    r"|(?:mon|tues|wednes|thurs|fri|satur|sun)day (?:blues|jazz|bluegrass|folk|funk|soul|swing)"
    r"|live (?:jazz|blues|bluegrass|folk|country|rock|soul|funk|acoustic|band|bands|entertainment))\b"
    r"|\w+fest\b|^\W*free\W*$",
    re.IGNORECASE,
)
# "Còig - early show", "Elderbrook - Heart On A Wire Tour", "2hollis: The Pirouette Tour":
# after a spaced dash or a colon comes the show's name, not more of the artist's.
# a dash needs a space on one side ("the Holidays- Sportsmens"), so "GA-20" and "Jay-Z" stay whole
SUBTITLE_RE = re.compile(r"\s*:\s+|\s+[-–—]\s*|\s*[-–—]\s+")
# "Connor Garvey & Ben Cosgrove": two acts billed together
DUO_RE = re.compile(r"\s+(?:&|and)\s+", re.IGNORECASE)
# "Chris Cote and his Band of These Guys": a leader and their backing band
BACKING_BAND_RE = re.compile(r"^(?:his|her|their)\b", re.IGNORECASE)
# words that name an occasion rather than an artist: "Built to Spill Fall 2026 Tour",
# "BUFFALO TOM 3rd Annual charity concert". compared normalized
OCCASION_WORDS = {
    "tour", "annual", "anniversary", "concert", "show", "celebration", "residency", "release",
    "holiday", "holidays", "christmas", "benefit", "charity", "reunion", "farewell", "birthday", "edition",
}
# "Rhiannon Hurst (21+)", "49th & Main (DJ Set)": notes after a name, not part of it.
# "Graphic Melee [EARLY SHOW]": a note in brackets is never part of a name.
# "with Jacyn Tremblay", "members of SixFoxWhiskey": words before the name.
# "Alan Kaufman & friends": the name and unnamed guests ("Sammy Rae & The Friends" is a band)
TRAILING_NOTE_RE = re.compile(
    r"\s*\(\s*(?:\d+\s*\+|all ages|dj set|live set|live|acoustic|solo|full band|sold out)\s*\)\s*$"
    r"|\s*\[[^\]]*\]\s*$",
    re.IGNORECASE,
)
LEADING_WITH_RE = re.compile(r"^(?:with|members of)\s+", re.IGNORECASE)
AND_FRIENDS_RE = re.compile(r"\s+(?:&|and|\+)\s+(?:friends|guests|special guests|band)$", re.IGNORECASE)
# what bills say in place of a name, compared normalized
PLACEHOLDERS = {"tba", "tbd", "special guest", "special guests", "and more", "more", "organization", "dj"}


# "Seb Lowe US 2027", "Built to Spill Fall 2026 Tour": a tour named after the act with no
# dash or colon between. words a trailing tour name is made of, dropped only when the run
# has a year, or "tour" and a region or season, so "Summer Salt" and "North Mississippi
# Allstars" stay whole
TOUR_YEAR_RE = re.compile(r"^(?:19|20)\d\d$")
TOUR_WORDS = {
    "us", "usa", "uk", "eu", "north", "south", "east", "west", "coast", "american", "america",
    "european", "europe", "canada", "canadian", "world", "worldwide", "global", "international",
    "fall", "autumn", "spring", "summer", "winter", "headline", "headlining", "dates", "leg",
}
# "The Thing in the Spring 2027": a little word before the run means it's part of the name
TOUR_NAME_JOINERS = {"the", "a", "an", "in", "of", "at", "on", "for", "to", "from", "and", "&", "with", "by"}


def strip_tour_name(name):
    """the name without a trailing tour name: "Seb Lowe US 2027" -> "Seb Lowe" """
    words = name.split()
    end, year, tour, place = len(words), False, False, False
    while end > 1:
        word = words[end - 1].strip("()[]'\"’.,!:").lower()
        if TOUR_YEAR_RE.match(word):
            year = True
        elif word in ("tour", "tours"):
            tour = True
        elif word in TOUR_WORDS:
            place = True
        else:
            break
        end -= 1
    # a lone "tour" is left for occasion_prefix, which needs it: "Corey Kent Heartland Rock and Roll Tour"
    marked = year or (tour and place)
    if not marked or end == len(words) or words[end - 1].lower() in TOUR_NAME_JOINERS:
        return name
    return " ".join(words[:end])


def clean_name(name):
    name, before = SUBTITLE_RE.split(name.strip(), maxsplit=1)[0], None
    # notes can stack: "Glass Halo (DJ Set) (21+)"
    while name != before:
        before, name = name, TRAILING_NOTE_RE.sub("", name)
    return strip_tour_name(AND_FRIENDS_RE.sub("", LEADING_WITH_RE.sub("", name).strip()))


SHOW_NAME_END_RE = re.compile(r"\btours?\W*$", re.IGNORECASE)


def split_names(text):
    """
    the names in a bill. after a show name, a comma piece ending "tour" is more of it: "Bo
    Staloch - The 'Too Big, Too Big' Tour" names one act, but "Còig - early show, Highway
    Kind" names two
    """
    # str(): a title or artists value needn't be a string until the event is saved
    pieces = re.split(f"({SEPARATOR_RE.pattern})", str(text or ""), flags=re.IGNORECASE)
    names, in_show_name = [], False
    for piece, separator in zip(pieces[::2], [""] + pieces[1::2]):
        if in_show_name and separator.strip() == "," and SHOW_NAME_END_RE.search(piece):
            continue
        in_show_name = bool(SUBTITLE_RE.search(piece.strip()))
        names.append(clean_name(piece))
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
