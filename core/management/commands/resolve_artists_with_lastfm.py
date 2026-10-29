import datetime

from core import apple_music
from core.apple_music import AppleMusicClient, AppleMusicError
from core.artist_evidence import covered_places, is_covered_subdivision, is_dominant, names_covered_place, shares_name
from core.artist_matching import normalize
from core.artist_names import event_artist_names
from core.job_runs import RecordedCommand
from core.lastfm import LastFm, LastFmError, LastFmStopped, api_key
from core.models import AppleMusicArtistLink, SpotifyArtistLink
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from core.spotify_links import rebake_events_naming, upcoming_music_events
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

"""
settles artist names that several spotify or apple music artists share, on evidence from
last.fm and musicbrainz, for the listing's play buttons. nothing from last.fm is shown or
kept (see openspec/specs/lastfm-artist-evidence).

run as:

python manage.py resolve_artists_with_lastfm [--names "Bonobo"] [--limit 300] [--dry-run] [--revert]

for each ambiguous automatic link an upcoming event names, it reads the name's last.fm page
for its musicbrainz id, and musicbrainz for that artist's spotify and apple music links. a
link is matched to the linked artist only when musicbrainz names it as we do, links exactly
one artist on that service, and the act is local (musicbrainz's area is in a covered state,
by its "part of" links, or the last.fm bio names a covered state and no other act) or dominant (last.fm counts at least 100,000 listeners, and
its bio doesn't say several acts share the name: see core/artist_evidence.py).

matched links get the source "evidence": the spotify and apple music matching keep them like
an editor's. each is re-checked after RECHECK_AFTER, and set back to ambiguous when the
evidence is gone. ambiguous links are looked at once per RECHECK_AFTER. --revert sets every
evidence link back to ambiguous.

needs LASTFM_API_KEY, and does nothing without it. last.fm rate-limiting or suspending the
key, or musicbrainz staying busy, stops the run, keeping what it found.
"""

RECHECK_AFTER = datetime.timedelta(days=30)
DEFAULT_LIMIT = 300
MODELS = {"spotify": SpotifyArtistLink, "apple": AppleMusicArtistLink}
ID_FIELDS = {"spotify": "spotify_artist_id", "apple": "apple_artist_id"}


def verdict(key, info, artist, places, music_ids):
    """
    ("local" or "dominant", why) when the evidence names this act as ours, else (None, why
    not), so every line of the report says which source decided it
    """
    if not info:
        return None, "no Last.fm page"
    if not info["mbid"]:
        return None, "the Last.fm page has no MusicBrainz ID"
    if not artist:
        return None, "MusicBrainz has no artist for the Last.fm page's ID"
    if normalize(artist["name"]) != key:
        return None, f'MusicBrainz calls the Last.fm page\'s act "{artist["name"]}"'
    areas = []
    for area in artist["areas"]:
        code = music_ids.area_subdivision(area["id"])
        if is_covered_subdivision(code, places):
            return "local", f"MusicBrainz area {area['name']} ({code})"
        areas.append(f"{area['name']} ({code})" if code else area["name"])
    # a shared page's bio describes several acts, so its places could be any of theirs
    if shares_name(info["bio"]):
        return None, "Last.fm says several acts share the name"
    if names_covered_place(info["bio"], places):
        return "local", "the Last.fm bio names a covered state"
    if is_dominant(info["listeners"], info["bio"]):
        return "dominant", f"{info['listeners']:,} Last.fm listeners"
    where = f"MusicBrainz area {', '.join(areas)}" if areas else "no MusicBrainz area"
    return None, f"neither local nor dominant: {info['listeners']:,} Last.fm listeners, {where}"


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--names", help="comma-separated artist names to consider, if due")
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="consider at most this many names")
        parser.add_argument("--dry-run", action="store_true", help="report what would be matched, but save nothing")
        parser.add_argument("--revert", action="store_true", help="set every evidence link back to ambiguous")

    def handle(self, *args, **options):
        if options["revert"]:
            return self.revert(options["dry_run"])
        key = api_key()
        if not key:
            self.stdout.write("last.fm isn't configured (LASTFM_API_KEY): nothing to do")
            return
        self.dry_run = options["dry_run"]
        self.now = timezone.now()
        self.counts = {
            "considered": 0, "resolved as local": 0, "resolved as dominant": 0, "stayed ambiguous": 0,
            "re-checked": 0, "reverted": 0, "failed": 0, "left for the next run": 0,
        }
        self.changed = set()
        lastfm, music_ids = LastFm(key), MusicIds()
        credentials = apple_music.credentials()
        self.apple = AppleMusicClient(*credentials) if credentials else None

        events = [event for event in upcoming_music_events() if event.is_music_kind]
        names = {}
        for event in events:
            for name in event_artist_names(event):
                names.setdefault(normalize(name), name)
        due = self.due_links(names)
        keys = sorted(due)
        if options["names"]:
            wanted = {normalize(name) for name in options["names"].split(",")}
            keys = [k for k in keys if k in wanted]
        keys = keys[: options["limit"]]
        places = covered_places()

        heading = "would record" if self.dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(keys)} names due)"))
        stopped = ""
        for index, k in enumerate(keys):
            try:
                info = lastfm.artist_info(names[k])
                artist = music_ids.artist(info["mbid"]) if info and info["mbid"] else None
                found = verdict(k, info, artist, places, music_ids)
            except (LastFmStopped, MusicBrainzBusy) as e:
                self.counts["failed"] += 1
                self.counts["left for the next run"] = len(keys) - index
                stopped = str(e)
                self.stdout.write(self.style.WARNING(f"  {names[k]}: {e}; stopping this run"))
                break
            except (LastFmError, MusicIdsError) as e:
                self.counts["failed"] += 1
                self.stdout.write(self.style.WARNING(f"  {names[k]}: failed: {e}"))
                continue
            self.counts["considered"] += 1
            for service, link in due[k].items():
                self.settle(service, link, names[k], found, artist)

        rebaked = 0 if self.dry_run else rebake_events_naming(self.changed, events)
        self.stdout.write(f"\nre-rendered {rebaked} events")
        self.job_summary = list(self.counts.items())
        if stopped:
            self.stdout.write(self.style.WARNING(f"stopped early, {self.counts['left for the next run']} names left: {stopped}"))

    def due_links(self, names):
        """{name key: {service: link}} for the links to look at now"""
        stale = self.now - RECHECK_AFTER
        due = {}
        for service, model in MODELS.items():
            links = model.objects.filter(name_key__in=names).filter(
                Q(source=model.Source.AUTO, status=model.Status.AMBIGUOUS)
                & (Q(evidence_checked_at__isnull=True) | Q(evidence_checked_at__lt=stale))
                | Q(source=model.Source.EVIDENCE, evidence_checked_at__lt=stale)
            )
            for link in links:
                due.setdefault(link.name_key, {})[service] = link
        return due

    def settle(self, service, link, name, found, artist):
        model = MODELS[service]
        ids = (artist or {}).get(service) or set()
        label = "Spotify" if service == "spotify" else "Apple Music"
        kind, why = found
        if kind and len(ids) != 1:
            why = f"MusicBrainz links {'no' if not ids else len(ids)} {label} artist{'' if len(ids) == 1 else 's'}"
        if kind and len(ids) == 1:
            artist_id = next(iter(ids))
            was_evidence = link.source == model.Source.EVIDENCE
            values = {
                "status": model.Status.MATCHED, ID_FIELDS[service]: artist_id, "source": model.Source.EVIDENCE,
                "checked_at": self.now, "evidence_checked_at": self.now,
            }
            if service == "apple":
                song = self.top_song(name, artist_id)
                if song is False:
                    return
                values.update(top_song_id=song["song_id"], top_album_id=song["album_id"])
            self.counts["re-checked" if was_evidence else f"resolved as {kind}"] += 1
            self.stdout.write(f"  {name}: {label} {'still ' if was_evidence else ''}{artist_id} ({kind}: {why})")
            if not was_evidence or getattr(link, ID_FIELDS[service]) != artist_id:
                self.changed.add(link.name_key)
            self.save(model, link, values)
            return
        if link.source == model.Source.EVIDENCE:
            self.counts["reverted"] += 1
            self.stdout.write(f"  {name}: {label} evidence gone, ambiguous again ({why})")
            self.changed.add(link.name_key)
            self.save(model, link, self.ambiguous(service, model))
            return
        self.counts["stayed ambiguous"] += 1
        self.stdout.write(f"  {name}: {label} stays ambiguous ({why})")
        self.save(model, link, {"evidence_checked_at": self.now})

    def top_song(self, name, artist_id):
        """the artist's top song ids (blank when it has none), or False when the lookup failed"""
        empty = {"song_id": "", "album_id": ""}
        if self.apple is None:
            return empty
        try:
            return self.apple.top_song(artist_id) or empty
        except AppleMusicError as e:
            self.counts["failed"] += 1
            self.stdout.write(self.style.WARNING(f"  {name}: apple music top song failed: {e}"))
            return False

    def ambiguous(self, service, model):
        values = {
            "status": model.Status.AMBIGUOUS, ID_FIELDS[service]: "", "source": model.Source.AUTO,
            "checked_at": self.now, "evidence_checked_at": self.now,
        }
        if service == "apple":
            values.update(top_song_id="", top_album_id="")
        return values

    def save(self, model, link, values):
        if not self.dry_run:
            model.objects.filter(pk=link.pk).update(**values)

    def revert(self, dry_run):
        self.now = timezone.now()
        keys, total = set(), 0
        for service, model in MODELS.items():
            links = model.objects.filter(source=model.Source.EVIDENCE)
            keys |= set(links.values_list("name_key", flat=True))
            total += links.count()
            if not dry_run:
                links.update(**self.ambiguous(service, model))
        rebaked = 0 if dry_run else rebake_events_naming(keys)
        self.stdout.write(f"{'would revert' if dry_run else 'reverted'} {total} evidence links; re-rendered {rebaked} events")
        self.job_summary = [("reverted", total)]
