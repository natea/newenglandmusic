"""
finds artists' and bands' musicbrainz artists and stores their open data
(enrich_artists_from_musicbrainz): type, country, area, dates, genres, links, and a band's
members.

a search is accepted only for a candidate whose name (or an alias) is the record's and
whose type is the record's kind, and:
- when it's the only one, unless musicbrainz places it in another state or country than
  the record's (its fuzzy search finds "Horse" from england for any band called horse);
- when there are several, the one in a state the site covers, or else the one whose
  musicbrainz id last.fm's page for the name gives, unless that page says several acts
  share the name.
nothing from last.fm is kept: its answer is used while choosing, then dropped.

a record whose musicbrainz id came from the import or an editor is looked up by that id,
not searched for, and its id is never replaced.
"""

from django.db.models import Q
from django.utils import timezone

from core.artist_evidence import covered_places, shares_name
from core.artist_matching import normalize
from core.artists import is_bandcamp_url
from core.models import Artist, Band, BandMembership, MusicAct

Status = MusicAct.MusicBrainzStatus
MUSICBRAINZ = "musicbrainz"
# musicbrainz's types for each kind of record
TYPES = {Artist: {"Person"}, Band: {"Group", "Orchestra", "Choir"}}
SEARCH_TYPES = {Artist: "person", Band: "group"}
# musicbrainz's member attributes that aren't a role
NOT_ROLES = {"original", "additional", "founder", "minor", "guest"}
# url relationship types -> how each is kept
URL_TYPES = ("official homepage", "bandcamp", "wikidata", "discogs")


def years(date):
    """"2011-05-01" -> 2011; None for no date"""
    try:
        return int((date or "")[:4])
    except ValueError:
        return None


def names(candidate):
    return {normalize(candidate.get("name"))} | {normalize(a.get("name")) for a in candidate.get("aliases") or []}


def exact_candidates(results, record):
    """the search results whose name or alias is the record's and whose type is its kind"""
    types = TYPES[type(record)]
    return [c for c in results if c.get("type") in types and record.name_key in names(c)]


class Matcher:
    """chooses a record's musicbrainz artist; `lastfm` is a core.lastfm client, or None"""

    def __init__(self, musicbrainz, lastfm=None, covered_states=None):
        self.musicbrainz = musicbrainz
        self.lastfm = lastfm
        if covered_states is None:
            covered_states = {f"US-{code}" for code in covered_places()["states"]}
        self.covered_states = covered_states

    def subdivision(self, candidate):
        """the iso code of the state its area or begin area is in ("US-MA"), or "" """
        for key in ("area", "begin-area"):
            area_id = (candidate.get(key) or {}).get("id")
            code = self.musicbrainz.area_subdivision(area_id) if area_id else ""
            if code:
                return code
        return ""

    def placed_elsewhere(self, candidate, record):
        if not record.state:
            return False
        code = self.subdivision(candidate)
        if code:
            return code != f"US-{record.state}"
        country = candidate.get("country") or ""
        return bool(country) and country != "US"

    def from_lastfm(self, record, candidates):
        if self.lastfm is None:
            return None
        info = self.lastfm.artist_info(record.name)
        if not info or shares_name(info["bio"]):
            return None
        return next((c for c in candidates if c["id"] == info["mbid"]), None)

    def choose(self, record):
        """(status, the chosen candidate's musicbrainz id or None)"""
        results = self.musicbrainz.search_artists(record.name, SEARCH_TYPES[type(record)])
        candidates = exact_candidates(results, record)
        if not candidates:
            return Status.NOT_FOUND, None
        if len(candidates) == 1:
            if self.placed_elsewhere(candidates[0], record):
                return Status.NOT_FOUND, None
            return Status.MATCHED, candidates[0]["id"]
        covered = [c for c in candidates if self.subdivision(c) in self.covered_states]
        if len(covered) == 1:
            return Status.MATCHED, covered[0]["id"]
        chosen = self.from_lastfm(record, candidates)
        if chosen:
            return Status.MATCHED, chosen["id"]
        return Status.AMBIGUOUS, None


def wikidata_id(url):
    """"https://www.wikidata.org/wiki/Q123" -> "Q123" """
    last = url.rstrip("/").rsplit("/", 1)[-1]
    return last if last[:1] == "Q" and last[1:].isdigit() else ""


def links(details):
    """{"website", "bandcamp_url", "wikidata_id", "discogs_url"} from the url relationships"""
    found = {}
    for relation in details.get("relations") or []:
        kind, url = relation.get("type"), ((relation.get("url") or {}).get("resource")) or ""
        if relation.get("target-type") != "url" or kind not in URL_TYPES or relation.get("ended"):
            continue
        if kind == "official homepage":
            found.setdefault("website", url)
        elif kind == "bandcamp" and is_bandcamp_url(url):
            found.setdefault("bandcamp_url", url)
        elif kind == "wikidata" and wikidata_id(url):
            found.setdefault("wikidata_id", wikidata_id(url))
        elif kind == "discogs":
            found.setdefault("discogs_url", url)
    return found


def members(details):
    """[{"id", "name", "role", "begin_year", "end_year"}] from a band's "member of band" links"""
    found = []
    for relation in details.get("relations") or []:
        artist = relation.get("artist") or {}
        if relation.get("type") != "member of band" or relation.get("direction") != "backward" or not artist.get("id"):
            continue
        role = ", ".join(a for a in relation.get("attributes") or [] if a not in NOT_ROLES)
        found.append({
            "id": artist["id"], "name": artist.get("name") or "", "role": role,
            "begin_year": years(relation.get("begin")), "end_year": years(relation.get("end")),
        })
    return found


def apply_details(record, details, status):
    """store what musicbrainz says about the record (not saved)"""
    life = details.get("life-span") or {}
    record.musicbrainz_id = details["id"]
    record.musicbrainz_status = status
    record.mb_type = details.get("type") or ""
    record.country = (details.get("country") or "")[:2]
    record.area = ((details.get("area") or {}).get("name") or "")[:255]
    record.begin_date = (life.get("begin") or "")[:10]
    record.end_date = (life.get("end") or "")[:10]
    # genres are musicbrainz's supplementary data (cc by-nc-sa), credited in the admin
    record.genres = [g["name"] for g in sorted(details.get("genres") or [], key=lambda g: -(g.get("count") or 0))][:10]
    if record.field_sources.get("musicbrainz_id") not in ("import", "editor"):
        record.field_sources["musicbrainz_id"] = MUSICBRAINZ
    found = links(details)
    record.wikidata_id = found.get("wikidata_id", "")
    record.discogs_url = found.get("discogs_url", "")
    # the record's own website and bandcamp link stay; musicbrainz's fill only empty ones
    for name in ("website", "bandcamp_url"):
        if found.get(name) and (not getattr(record, name) or record.field_sources.get(name) == MUSICBRAINZ):
            setattr(record, name, found[name])
            record.field_sources[name] = MUSICBRAINZ


def member_artist(band, member):
    """the artist for a musicbrainz member: by id, then by name (in the band, then one with
    no musicbrainz id), else a new one"""
    artist = Artist.objects.filter(musicbrainz_id=member["id"]).first()
    if artist:
        return artist
    key = normalize(member["name"])
    in_band = band.members.filter(name_key=key, musicbrainz_id=None).first() if band.pk else None
    if in_band is None:
        others = list(Artist.objects.filter(name_key=key, musicbrainz_id=None)[:2])
        in_band = others[0] if len(others) == 1 else None
    if in_band:
        in_band.musicbrainz_id = member["id"]
        in_band.field_sources["musicbrainz_id"] = MUSICBRAINZ
        in_band.save()
        return in_band
    return Artist.objects.create(
        name=member["name"], musicbrainz_id=member["id"], field_sources={"musicbrainz_id": MUSICBRAINZ}
    )


def add_members(band, details):
    """musicbrainz's members as memberships; returns the names added. another source's
    membership of the same artist stays as it is, gaining only missing years"""
    added = []
    for member in members(details):
        artist = member_artist(band, member)
        existing = list(band.memberships.filter(artist=artist))
        if existing:
            for membership in existing:
                changed = False
                for name in ("begin_year", "end_year"):
                    if getattr(membership, name) is None and member[name] is not None:
                        setattr(membership, name, member[name])
                        changed = True
                if membership.source == BandMembership.Source.MUSICBRAINZ and membership.role != member["role"]:
                    membership.role, changed = member["role"], True
                if changed:
                    membership.save()
            continue
        BandMembership.objects.create(
            band=band, artist=artist, role=member["role"], begin_year=member["begin_year"],
            end_year=member["end_year"], source=BandMembership.Source.MUSICBRAINZ,
        )
        added.append(artist.name)
    return added


def enrich(record, musicbrainz, matcher):
    """
    looks the record up (by its id when it has one, else by a search), stores what's found
    and returns (status, members added). raises core.music_ids.MusicIdsError when musicbrainz
    can't be asked
    """
    now = timezone.now()
    if record.musicbrainz_id:
        status = Status.EDITOR if record.musicbrainz_status == Status.EDITOR else Status.MATCHED
        mbid = record.musicbrainz_id
    else:
        status, mbid = matcher.choose(record)
    details = musicbrainz.artist_details(mbid) if mbid else None
    added = []
    if details is None:
        if mbid and status != Status.EDITOR:
            # an id musicbrainz no longer knows
            status = Status.NOT_FOUND
        record.musicbrainz_status = status
    elif type(record).objects.filter(musicbrainz_id=details["id"]).exclude(pk=record.pk).exists():
        # another record is that artist already (a band's member, say): an editor merges them
        details = None
        record.musicbrainz_status = Status.AMBIGUOUS
    else:
        apply_details(record, details, status)
    record.musicbrainz_checked_at = now
    record.save()
    if details is not None and isinstance(record, Band):
        added = add_members(record, details)
    return record.musicbrainz_status, added


def due(model, refresh=False):
    """the records to look up: not checked yet, or all with refresh"""
    records = model.objects.order_by("name")
    return records if refresh else records.filter(Q(musicbrainz_checked_at__isnull=True))
