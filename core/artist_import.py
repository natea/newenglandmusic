"""
imports artists and bands from rows of a csv file or a google sheet tab (import_artists),
in one layout, keyed by Act_ID:

    Act_ID, Name, Kind, Members, Town, State, Website, Bandcamp, MusicBrainz_ID, Notes

Kind is "artist" or "band". a band's Members are separated by semicolons, each with an
optional role in parentheses: "Jonah Furman (bass, vocals); Aaron Mendelsohn (guitar)".

a row creates its record or updates it, and adds its members. the import never deletes a
record or a membership, and writes a field only when it's unset or the import's own (see
MusicAct.field_sources), so an editor's or musicbrainz's value stays.
"""

import csv
import re
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction

from core.artist_matching import normalize
from core.artists import MBID_PATTERN, is_bandcamp_url
from core.models import Artist, Band, BandMembership

COLUMNS = ("Act_ID", "Name", "Kind", "Members", "Town", "State", "Website", "Bandcamp", "MusicBrainz_ID", "Notes")
KINDS = {"artist": Artist, "band": Band}
# the fields each column sets
FIELD_COLUMNS = {
    "name": "Name",
    "city_town": "Town",
    "state": "State",
    "website": "Website",
    "bandcamp_url": "Bandcamp",
    "musicbrainz_id": "MusicBrainz_ID",
    "notes": "Notes",
}
IMPORT = "import"
MBID_RE = re.compile(MBID_PATTERN)
STATE_RE = re.compile(r"^[A-Z]{2}$")
# "Kim Gordon (bass, vocals)" -> name, role
MEMBER_RE = re.compile(r"^(?P<name>[^()]+?)\s*(?:\((?P<role>[^()]*)\))?$")


@dataclass
class ImportReport:
    created: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    members_added: list = field(default_factory=list)
    # (row number, Act_ID, what's wrong); a skipped row or a skipped value
    problems: list = field(default_factory=list)

    def summary(self):
        return [
            ("created", len(self.created)),
            ("updated", len(self.updated)),
            ("unchanged", len(self.unchanged)),
            ("members added", len(self.members_added)),
            ("problems", len(self.problems)),
        ]


def rows_from_csv(file):
    """a csv file's rows as dicts keyed by its header"""
    return [{(k or "").strip(): (v or "") for k, v in row.items()} for row in csv.DictReader(file)]


def split_members(text):
    """the list split at semicolons outside parentheses: "A (bass; vocals); B" is two"""
    parts, depth, current = [], 0, ""
    for char in text or "":
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == ";" and depth <= 0:
            parts.append(current)
            current, depth = "", 0
        else:
            current += char
    return [part.strip() for part in parts + [current] if part.strip()]


def parse_members(text, problem=None):
    """"A (bass); B" -> [("A", "bass"), ("B", "")]; an entry it can't read is reported"""
    members = []
    for part in split_members(text):
        match = MEMBER_RE.match(part)
        if match and match["name"].strip():
            members.append((" ".join(match["name"].split()), " ".join((match["role"] or "").split())))
        elif problem:
            problem(f"member {part!r} isn't a name with an optional (role); skipped")
    return members


def clean_values(row, problem):
    """the row's field values that are valid, reporting each one that isn't"""
    values = {name: (row.get(column) or "").strip() for name, column in FIELD_COLUMNS.items()}
    values["state"] = values["state"].upper()
    if values["state"] and not STATE_RE.match(values["state"]):
        problem(f"State {values['state']!r} isn't a two-letter code; not saved")
        del values["state"]
    if values["website"]:
        try:
            URLValidator(schemes=["http", "https"])(values["website"])
        except ValidationError:
            problem(f"Website {values['website']!r} isn't a web address; not saved")
            del values["website"]
    if values["bandcamp_url"] and not is_bandcamp_url(values["bandcamp_url"]):
        problem(f"Bandcamp {values['bandcamp_url']!r} isn't a bandcamp.com page; not saved")
        del values["bandcamp_url"]
    values["musicbrainz_id"] = values["musicbrainz_id"].lower()
    if values["musicbrainz_id"] and not MBID_RE.match(values["musicbrainz_id"]):
        problem(f"MusicBrainz_ID {values['musicbrainz_id']!r} isn't a MusicBrainz id; not saved")
        del values["musicbrainz_id"]
    return values


def apply_values(record, values):
    """set the values the import may (unset or its own); returns whether anything changed"""
    changed = False
    for name, value in values.items():
        if record.field_sources.get(name, IMPORT) != IMPORT:
            continue
        if name == "musicbrainz_id":
            value = value or None
        if getattr(record, name) != value:
            setattr(record, name, value)
            changed = True
            if name == "musicbrainz_id":
                # a new id from the sheet is looked up by the next enrichment
                record.musicbrainz_status = ""
                record.musicbrainz_checked_at = None
        if value:
            record.field_sources[name] = IMPORT
        else:
            record.field_sources.pop(name, None)
    return changed


def find_member(band, name):
    """the artist a band's member list means: one already in the band, else any with the name"""
    key = normalize(name)
    in_band = [m.artist for m in band.memberships.select_related("artist") if m.artist.name_key == key]
    if in_band:
        return in_band[0], False
    existing = Artist.objects.filter(name_key=key).order_by("pk").first()
    if existing:
        return existing, False
    return Artist.objects.create(name=name), True


def add_members(band, members, report):
    for name, role in members:
        artist, _ = find_member(band, name)
        current = list(band.memberships.filter(artist=artist))
        if any(m.role == role for m in current):
            continue
        own = [m for m in current if m.source == BandMembership.Source.IMPORT]
        if len(own) == 1:
            # the sheet changed this member's role
            own[0].role = role
            own[0].save(update_fields=["role"])
        else:
            BandMembership.objects.create(band=band, artist=artist, role=role, source=BandMembership.Source.IMPORT)
        report.members_added.append(f"{artist.name} in {band.name}" + (f" ({role})" if role else ""))


def adoptable(model, name):
    """the one record with this name and no Act_ID (made as a band's member), if just one"""
    candidates = list(model.objects.filter(name_key=normalize(name), act_id=None)[:2])
    return candidates[0] if len(candidates) == 1 else None


def import_row(number, row, report):
    act_id = (row.get("Act_ID") or "").strip()

    def problem(message):
        report.problems.append((number, act_id, message))

    if not act_id:
        return problem("no Act_ID; row skipped")
    if not (row.get("Name") or "").strip():
        return problem("no Name; row skipped")
    kind = (row.get("Kind") or "").strip().lower()
    if kind not in KINDS:
        return problem(f"Kind {row.get('Kind')!r} isn't artist or band; row skipped")
    model, other = KINDS[kind], KINDS["band" if kind == "artist" else "artist"]
    if other.objects.filter(act_id=act_id).exists():
        return problem(f"{act_id} is already a{'n artist' if kind == 'band' else ' band'}; row skipped")

    values = clean_values(row, problem)
    mbid = values.get("musicbrainz_id")
    if mbid and model.objects.filter(musicbrainz_id=mbid).exclude(act_id=act_id).exists():
        problem(f"MusicBrainz_ID {mbid} is already another {kind}'s; not saved")
        del values["musicbrainz_id"]

    record = model.objects.filter(act_id=act_id).first() or adoptable(model, values["name"])
    created = record is None
    if created:
        record = model(act_id=act_id)
    elif not record.act_id:
        # a member made from a band's list, now with its own row
        record.act_id = act_id
        record.save(update_fields=["act_id"])
    changed = apply_values(record, values)
    if created or changed:
        record.save()
    label = f"{act_id} {record.name}"
    (report.created if created else report.updated if changed else report.unchanged).append(label)

    members = parse_members(row.get("Members"), problem)
    if members and kind == "artist":
        problem("Members is for bands; ignored for an artist")
    elif members:
        add_members(record, members, report)


def import_rows(rows, dry_run=False):
    """imports the rows, in one transaction; a dry run rolls it back. returns an ImportReport"""
    report = ImportReport()
    with transaction.atomic():
        # row 1 is the header, so the first data row is row 2, as in the sheet
        for number, row in enumerate(rows, start=2):
            import_row(number, row, report)
        if dry_run:
            transaction.set_rollback(True)
    return report
