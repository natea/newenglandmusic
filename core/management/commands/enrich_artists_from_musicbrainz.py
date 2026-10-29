from contextlib import nullcontext

from core import lastfm
from core.artist_enrichment import Matcher, due, enrich
from core.job_runs import RecordedCommand
from core.models import Artist, Band
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from core.wikipedia import Wikipedia
from django.core.management.base import BaseCommand
from django.db import transaction

"""
finds each artist's and band's musicbrainz artist, and stores its id and open data: type,
country, area, dates, genres, links (official site, bandcamp, wikidata, discogs), a band's
members, musicbrainz's disambiguation note, and the opening paragraph of its english
wikipedia article when musicbrainz links it to wikidata (cc by-sa: credited wherever it's
shown, see core/wikipedia.py). see core/artist_enrichment.py for how a match is chosen.

run as:

python manage.py enrich_artists_from_musicbrainz [--limit 20] [--refresh] [--dry-run]

bands go first, then artists, so a run can fill in members it made. records checked before
are skipped unless --refresh. musicbrainz asks for one request a second: each record costs
a search and a lookup (one lookup when its id is known), plus a few area lookups to place
candidates, so about 2 seconds a record. last.fm (LASTFM_API_KEY) is asked only when a name
matches several musicbrainz artists, and nothing from it is kept; without a key, those
records are left ambiguous. a record with a wikidata id costs two more requests, to
wikidata and wikipedia. nothing is requested from bandcamp.
"""


class Command(RecordedCommand, BaseCommand):
    help = "find artists' and bands' musicbrainz artists and store their open data"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="look up at most this many records")
        parser.add_argument("--refresh", action="store_true", help="look up records checked before too")
        parser.add_argument("--dry-run", action="store_true", help="report what would be stored, and save nothing")

    def handle(self, *args, **options):
        musicbrainz = MusicIds()
        self.lastfm = lastfm.client() if lastfm.api_key() else None
        if self.lastfm is None:
            self.stdout.write("LASTFM_API_KEY isn't set: names several acts share stay ambiguous")
        matcher = Matcher(musicbrainz, lastfm=self)
        wikipedia = Wikipedia()
        records = list(due(Band, options["refresh"])) + list(due(Artist, options["refresh"]))
        if options["limit"]:
            records = records[: options["limit"]]
        counts = {
            "matched": 0, "editor": 0, "ambiguous": 0, "not_found": 0, "members added": 0,
            "with wikipedia text": 0, "failed": 0, "wikipedia failed": 0,
        }
        heading = "would record" if options["dry_run"] else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(records)} records)"))
        # a dry run rolls everything back at the end; a real run keeps each record as it's
        # saved, so a stopped run keeps what it found
        with transaction.atomic() if options["dry_run"] else nullcontext():
            for record in records:
                kind = "band" if isinstance(record, Band) else "artist"
                try:
                    problems = []
                    with transaction.atomic():
                        status, added = enrich(record, musicbrainz, matcher, wikipedia, problems)
                except MusicBrainzBusy as e:
                    counts["failed"] += 1
                    self.stdout.write(self.style.WARNING(f"  {record.name}: {e}; stopping this run"))
                    break
                except MusicIdsError as e:
                    counts["failed"] += 1
                    self.stdout.write(self.style.WARNING(f"  {record.name}: {e}"))
                    continue
                counts[status] += 1
                counts["members added"] += len(added)
                counts["with wikipedia text"] += bool(record.wikipedia_extract)
                counts["wikipedia failed"] += len(problems)
                for problem in problems:
                    self.stdout.write(self.style.WARNING(f"  {problem}"))
                found = f" {record.musicbrainz_id}" if record.musicbrainz_id else ""
                members = f", members added: {', '.join(added)}" if added else ""
                wiki = f", wikipedia: {record.wikipedia_url}" if record.wikipedia_extract else ""
                self.stdout.write(f"  {kind} {record.name}: {status}{found}{members}{wiki}")
            if options["dry_run"]:
                transaction.set_rollback(True)
        self.job_summary = list(counts.items())

    def artist_info(self, name):
        """the matcher's last.fm evidence; a stopped key or an error just means no evidence"""
        if self.lastfm is None:
            return None
        try:
            return self.lastfm.artist_info(name)
        except lastfm.LastFmStopped as e:
            self.stdout.write(self.style.WARNING(f"  last.fm stopped us ({e}); not asking it again this run"))
            self.lastfm = None
        except lastfm.LastFmError:
            pass
        return None
