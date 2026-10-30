import csv
import datetime
from collections import defaultdict
from contextlib import nullcontext

from core import lastfm
from core.artist_enrichment import NOT_ON_MUSICBRAINZ, Matcher, choose_kind
from core.artist_import import COLUMNS
from core.artist_matching import normalize
from core.artist_names import event_artist_names, name_parts
from core.event_performers import link_from_names, names_to_records
from core.job_runs import RecordedCommand
from core.management.commands.enrich_artists_from_musicbrainz import Command as EnrichCommand
from core.models import Artist, Band, Event
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

"""
makes artist and band records from the names in approved events' titles and artists
column, then links every approved event to the records its names are. titles count because
every source puts the headliner there and leaves it out of the artists column.

run as:

python manage.py import_artists_from_events [--limit 50] [--dry-run] [--review-csv path]

each name is searched on musicbrainz as a person and as a group (core/artist_enrichment.py's
choose_kind): one settled as exactly one kind becomes that record, with its musicbrainz id,
for enrich_artists_from_musicbrainz to fill in. nothing is guessed: every other name is
written to the review csv (logs/artists-from-events-review-<date>.csv), in import_artists'
layout with Act_ID and Kind blank, for an editor to fill in and import.

a duo billing that isn't on musicbrainz as a whole ("Louis Cole & Chiquita Magic") has
each of its acts looked up instead, and only the acts not found go on the review list; when
none is found, the billing goes there whole, as it may be one band ("Dust Bowls and Jewish
Souls").

names already an artist's or a band's, and placeholders ("TBA"), are skipped; the names most
events give go first, so --limit covers the acts that matter most. about two searches a
name at musicbrainz's one request a second. a busy musicbrainz stops the run, keeping the
records made, and the next run starts where it left off.
"""

REVIEW_COLUMNS = (*COLUMNS, "Reason", "Events", "Example_Event")


def named_events():
    """approved events with a title or artists"""
    return Event.objects.exclude(Q(artists=None) | Q(artists=""), Q(title=None) | Q(title=""))


def event_names():
    """
    {name_key: {"name", "events", "example"}} from approved events' titles and artists, most-
    named first. titles count: every source puts the headliner there and leaves it out of
    the artists (2026-10-29)
    """
    found = {}
    counts = defaultdict(int)
    for event in named_events().select_related("venue").order_by("starttime"):
        for name in event_artist_names(event):
            key = normalize(name)
            counts[key] += 1
            if key not in found:
                venue = event.venue.name if event.venue else ""
                found[key] = {"name": name, "example": f"{event.starttime:%Y-%m-%d} {event.title} @ {venue}".strip()}
    for key, entry in found.items():
        entry["events"] = counts[key]
    return dict(sorted(found.items(), key=lambda item: (-item[1]["events"], item[1]["name"].lower())))


def whole_billings(review):
    """
    the review list with a duo billing none of whose acts was found back as one name: "Dust
    Bowls and Jewish Souls" may be one band, and an editor can split it if not
    """
    review_keys = {normalize(entry["name"]) for entry in review}
    whole, seen = [], set()
    for entry in review:
        billing = entry.get("billing")
        if billing and all(normalize(part) in review_keys for part in name_parts(billing["name"])):
            if normalize(billing["name"]) not in seen:
                seen.add(normalize(billing["name"]))
                whole.append({**billing, "reason": entry["reason"]})
            continue
        whole.append(entry)
    return whole


class Command(RecordedCommand, BaseCommand):
    help = "make artist and band records from events' artists, and link the events to them"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="look up at most this many names")
        parser.add_argument("--dry-run", action="store_true", help="report and write the review list, and save nothing")
        parser.add_argument("--review-csv", help="where to write the review list")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        review_path = options["review_csv"] or f"logs/artists-from-events-review-{datetime.date.today():%Y-%m-%d}.csv"
        existing = set(Artist.objects.values_list("name_key", flat=True)) | set(Band.objects.values_list("name_key", flat=True))
        names = [(key, entry) for key, entry in event_names().items() if key not in existing]
        if options["limit"]:
            names = names[: options["limit"]]

        # last.fm only helps choose between musicbrainz artists, as in the enrichment
        self.lastfm = lastfm.client() if lastfm.api_key() else None
        if self.lastfm is None:
            self.stdout.write("LASTFM_API_KEY isn't set: names several acts share go on the review list")
        matcher = Matcher(MusicIds(), lastfm=self)
        counts = {"bands made": 0, "artists made": 0, "for review": 0, "failed": 0, "events linked": 0}
        review = []
        heading = "would make" if dry_run else "made"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(names)} names to look up)"))
        queued = existing | {key for key, entry in names}
        with transaction.atomic() if dry_run else nullcontext():
            while names:
                key, entry = names.pop(0)
                try:
                    model, mbid, reason = choose_kind(entry["name"], matcher)
                except MusicBrainzBusy as e:
                    counts["failed"] += 1
                    self.stdout.write(self.style.WARNING(f"  {entry['name']}: {e}; stopping this run"))
                    break
                except MusicIdsError as e:
                    counts["failed"] += 1
                    self.stdout.write(self.style.WARNING(f"  {entry['name']}: {e}"))
                    continue
                if model is None and reason == NOT_ON_MUSICBRAINZ and name_parts(entry["name"]):
                    # its acts go next, each looked up as a name of its own
                    parts = [part for part in name_parts(entry["name"]) if normalize(part) not in queued]
                    for part in reversed(parts):
                        queued.add(normalize(part))
                        names.insert(0, (normalize(part), {**entry, "name": part, "billing": entry}))
                    self.stdout.write(f"  {entry['name']}: not on MusicBrainz; looking up its acts")
                    continue
                if model is None:
                    counts["for review"] += 1
                    review.append({**entry, "reason": reason})
                    self.stdout.write(f"  for review: {entry['name']} ({reason})")
                    continue
                if self.make(model, entry["name"], mbid):
                    counts["bands made" if model is Band else "artists made"] += 1
                    self.stdout.write(f"  {model.__name__.lower()} {entry['name']} {mbid}")
            counts["events linked"] = self.link_events()
            if dry_run:
                transaction.set_rollback(True)
        review = whole_billings(review)
        self.write_review(review_path, review)
        self.job_summary = list(counts.items())
        self.stdout.write(f"\nreview list: {review_path} ({len(review)} names)")
        self.stdout.write(f"events linked to their artists and bands: {counts['events linked']}")

    def make(self, model, name, mbid):
        """
        a record with just the name and the musicbrainz id, which enrichment looks up; None
        when musicbrainz's artist is a record already, under another spelling
        """
        clash = model.objects.filter(musicbrainz_id=mbid).first()
        if clash:
            self.stdout.write(f"  {name}: musicbrainz's artist is already {clash.name}")
            return None
        return model.objects.create(name=name, musicbrainz_id=mbid, field_sources={"musicbrainz_id": "musicbrainz"})

    def link_events(self):
        """links every approved event to the records its names are; returns how many have any"""
        records = names_to_records()
        linked = 0
        with transaction.atomic():
            for event in named_events():
                link_from_names(event, records)
                linked += event.performers.exists()
        return linked

    def write_review(self, path, review):
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=REVIEW_COLUMNS)
            writer.writeheader()
            for entry in review:
                writer.writerow({
                    "Name": entry["name"], "Reason": entry["reason"], "Events": entry["events"],
                    "Example_Event": entry["example"],
                })

    # the matcher's last.fm evidence, handled as the enrichment does
    artist_info = EnrichCommand.artist_info
