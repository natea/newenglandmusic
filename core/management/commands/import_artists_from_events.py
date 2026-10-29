import csv
import datetime
from collections import defaultdict
from contextlib import nullcontext

from core import lastfm
from core.artist_enrichment import Matcher, choose_kind
from core.artist_import import COLUMNS
from core.artist_matching import normalize
from core.artist_names import is_placeholder, split_names
from core.event_performers import link_from_names, names_to_records
from core.job_runs import RecordedCommand
from core.management.commands.enrich_artists_from_musicbrainz import Command as EnrichCommand
from core.models import Artist, Band, Event
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from django.core.management.base import BaseCommand
from django.db import transaction

"""
makes artist and band records from the names in approved events' artists column, then
links every approved event to the records its names are.

run as:

python manage.py import_artists_from_events [--limit 50] [--dry-run] [--review-csv path]

each name is searched on musicbrainz as a person and as a group (core/artist_enrichment.py's
choose_kind): one settled as exactly one kind becomes that record, with its musicbrainz id,
for enrich_artists_from_musicbrainz to fill in. nothing is guessed: every other name is
written to the review csv (logs/artists-from-events-review-<date>.csv), in import_artists'
layout with Act_ID and Kind blank, for an editor to fill in and import.

names already an artist's or a band's, and placeholders ("TBA"), are skipped; the names most
events give go first, so --limit covers the acts that matter most. about two searches a
name at musicbrainz's one request a second. a busy musicbrainz stops the run, keeping the
records made, and the next run starts where it left off.
"""

REVIEW_COLUMNS = (*COLUMNS, "Reason", "Events", "Example_Event")


def event_names():
    """{name_key: {"name", "events", "example"}} from approved events' artists, most-named first"""
    found = {}
    counts = defaultdict(int)
    events = Event.objects.exclude(artists=None).exclude(artists="").select_related("venue").order_by("starttime")
    for event in events:
        for name in split_names(event.artists):
            if is_placeholder(name):
                continue
            key = normalize(name)
            counts[key] += 1
            if key not in found:
                venue = event.venue.name if event.venue else ""
                found[key] = {"name": name, "example": f"{event.starttime:%Y-%m-%d} {event.title} @ {venue}".strip()}
    for key, entry in found.items():
        entry["events"] = counts[key]
    return dict(sorted(found.items(), key=lambda item: (-item[1]["events"], item[1]["name"].lower())))


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
        with transaction.atomic() if dry_run else nullcontext():
            for key, entry in names:
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
            for event in Event.objects.exclude(artists=None).exclude(artists=""):
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
