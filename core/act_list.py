"""
a curated list of acts imported as artists and bands (import_act_list): Sooz's Oh Hello
Boston tabs, or the next editor's list, each read in its own columns.

rows that name the same act, on one tab or across tabs, are merged into one act before
anything is looked up: the same name (core.artist_matching.normalize) or the same
musicbrainz id. each act's kind is musicbrainz's: its id's type, or a search of its name as
the events' names are searched, the list's Kind settling a name that's both. an act already
on the site is found, not made again; fields are filled only when unset or the list's own,
and the list's source key is added (MusicAct.sources).

the list is vetted, so every act becomes a record. one musicbrainz can't settle cleanly is
made held for review (MusicAct.needs_review, with its reasons): no public page, no event
links, until an editor marks it ready in the admin.
"""

from dataclasses import dataclass, field

from core.artist_enrichment import BOTH_KINDS, NOT_ON_MUSICBRAINZ, SEVERAL, choose_kind
from core.artist_import import FIELD_COLUMNS, clean_values
from core.artist_matching import normalize
from core.models import Artist, Band

# the list's own headers, compared lowercased, for each field
COLUMN_ALIASES = {
    "name": ("artist", "name", "band", "act"),
    "city_town": ("city", "town"),
    "state": ("state",),
    "website": ("website",),
    "bandcamp_url": ("bandcamp",),
    "instagram_url": ("instagram",),
    "youtube_url": ("youtube",),
    "musicbrainz_id": ("musicbrainz id", "musicbrainz_id", "mbid"),
    "kind": ("kind",),
}
KINDS = {"artist": Artist, "band": Band}
# musicbrainz's artist types and what each makes; anything else (character, other) is held
# for review. many acts have no type on musicbrainz: the list's Kind (else band) decides those
MB_TYPES = {"Person": Artist, "Group": Band, "Orchestra": Band, "Choir": Band}
# choose_kind's reasons as review codes (MusicAct.REVIEW_REASONS)
SEARCH_REASONS = {NOT_ON_MUSICBRAINZ: "not_found", SEVERAL: "several", BOTH_KINDS: "kind"}
STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


@dataclass
class Act:
    """one act, from one or more rows of the list"""

    name: str
    values: dict
    kind: str = ""
    tabs: list = field(default_factory=list)


@dataclass
class ListReport:
    made: list = field(default_factory=list)
    held: list = field(default_factory=list)  # made, held for review
    found: list = field(default_factory=list)
    # what the list said that couldn't be used, or that two of its rows said differently
    problems: list = field(default_factory=list)
    events_linked: int = 0

    def summary(self):
        return [
            ("made live", len(self.made)), ("held for review", len(self.held)), ("found", len(self.found)),
            ("problems", len(self.problems)), ("events linked", self.events_linked),
        ]


def state_code(value):
    """"MA" from "Massachusetts" or "ma"; anything else as given, for clean_values to report"""
    value = (value or "").strip()
    return STATE_CODES.get(value.lower(), value.upper())


def row_values(row, columns, problem):
    """the row's act fields, by the list's own headers, cleaned as import_artists cleans them"""
    found = {name: (row.get(columns[name]) or "").strip() if name in columns else "" for name in COLUMN_ALIASES}
    found["state"] = state_code(found["state"])
    # clean_values reads import_artists' layout: Name, Town, State, Website...
    layout = {FIELD_COLUMNS[name]: value for name, value in found.items() if name in FIELD_COLUMNS}
    values = clean_values(layout, problem)
    values.pop("notes", None)
    return values, found["kind"].lower()


def header_map(header):
    """{field: the list's column} from a tab's header row"""
    lowered = {column.strip().lower(): column for column in header}
    return {name: lowered[alias] for name, aliases in COLUMN_ALIASES.items() for alias in aliases if alias in lowered}


def merge_acts(tabs, report):
    """
    one Act per act named in the tabs [(tab name, rows)], in the order given: rows with the
    same name or musicbrainz id merged, the first value of each field kept and each
    different later one reported
    """
    acts, by_key, by_mbid = [], {}, {}
    for tab, rows in tabs:
        columns = header_map(rows[0].keys()) if rows else {}
        for number, row in enumerate(rows, start=2):
            name = (row.get(columns.get("name", "")) or "").strip()
            if not name:
                continue
            problem = lambda message: report.problems.append(f"{tab} row {number} ({name}): {message}")
            values, kind = row_values(row, columns, problem)
            key, mbid = normalize(name), values.get("musicbrainz_id")
            act = by_key.get(key) or (by_mbid.get(mbid) if mbid else None)
            if act is None:
                act = Act(name=name, values={}, kind=kind)
                acts.append(act)
            elif not act.kind:
                act.kind = kind
            act.tabs.append(tab)
            for name_, value in values.items():
                if not value or name_ == "name":
                    continue
                if not act.values.get(name_):
                    act.values[name_] = value
                elif act.values[name_] != value:
                    report.problems.append(f"{tab} gives {act.name} a different {name_} ({value}); kept {act.values[name_]}")
            by_key.setdefault(key, act)
            if act.values.get("musicbrainz_id"):
                by_mbid.setdefault(act.values["musicbrainz_id"], act)
    return acts


def placed_elsewhere(details, matcher):
    """whether musicbrainz places the act only outside the states the site covers"""
    country = details.get("country") or ""
    if country and country != "US":
        return True
    places = matcher.places(details)
    return bool(places) and not (places & matcher.covered_states)


def names_of(details):
    """the musicbrainz act's name and aliases, normalized"""
    return {normalize(details.get("name") or "")} | {normalize(a.get("name") or "") for a in details.get("aliases") or []}


def decide_kind(act, matcher, music_ids):
    """
    (Artist or Band, musicbrainz id or None, review codes) for the act: no codes when
    musicbrainz settles it cleanly, else why it's held for review
    """
    listed = KINDS.get(act.kind)
    mbid = act.values.get("musicbrainz_id")
    if mbid:
        # an act already on the site with this id is settled: no need to ask musicbrainz
        for model in (Band, Artist):
            if model.objects.filter(musicbrainz_id=mbid).exists():
                return model, mbid, []
        details = music_ids.artist_details(mbid)
        if not details:
            return listed or Band, None, ["id_unknown"]
        mb_type = details.get("type") or ""
        model = MB_TYPES.get(mb_type) if mb_type else (listed or Band)
        if model is None:
            return listed or Band, mbid, ["id_type"]
        reasons = [] if normalize(act.name) in names_of(details) else ["name"]
        if placed_elsewhere(details, matcher):
            reasons.append("elsewhere")
        return model, mbid, reasons
    model, mbid, reason = choose_kind(act.name, matcher, prefer=listed)
    if model is None:
        return listed or Band, None, [SEARCH_REASONS.get(reason, "not_found")]
    details = music_ids.artist_details(mbid) or {}
    return model, mbid, ["elsewhere"] if placed_elsewhere(details, matcher) else []


def find_record(model, name, mbid):
    """the act already on the site: by musicbrainz id (either kind), else by name and kind"""
    for kind in (model, Artist if model is Band else Band):
        record = kind.objects.filter(musicbrainz_id=mbid).first() if mbid else None
        if record:
            return record
    same_name = list(model.objects.filter(name_key=normalize(name)).order_by("pk")[:2])
    return same_name[0] if len(same_name) == 1 else None


def fill(record, values, source):
    """set each value the list may (the field unset, or the list's own); returns whether anything changed"""
    changed = False
    for name, value in values.items():
        if not value or name == "name":
            continue
        owner = record.field_sources.get(name)
        current = getattr(record, name)
        if owner == source or (owner is None and not current):
            if current != value:
                setattr(record, name, value)
                changed = True
                if name == "musicbrainz_id":
                    record.musicbrainz_status = ""
                    record.musicbrainz_checked_at = None
            record.field_sources[name] = source
    if source not in record.sources:
        record.sources = [*record.sources, source]
        changed = True
    return changed


def import_act(act, model, mbid, reasons, source, report):
    """make or find the act's record, fill it and mark its source; a made one with reasons is held for review"""
    values = {**act.values, "musicbrainz_id": mbid or ""}
    record = find_record(model, act.name, mbid)
    if record is None:
        record = model(name=act.name, needs_review=bool(reasons), review_reasons=reasons)
        fill(record, values, source)
        record.save()
        (report.held if reasons else report.made).append(record)
        return record
    if not isinstance(record, model):
        report.problems.append(f"{act.name}: MusicBrainz's act is already the {type(record).__name__.lower()} {record.name}; kept as it is")
    if record.musicbrainz_id and mbid and record.musicbrainz_id != mbid:
        values.pop("musicbrainz_id")
        report.problems.append(f"{act.name}: already has MusicBrainz ID {record.musicbrainz_id}; the list's {mbid} not used")
    if fill(record, values, source):
        record.save()
    report.found.append(record)
    return record


__all__ = ["Act", "ListReport", "decide_kind", "import_act", "merge_acts", "state_code"]
