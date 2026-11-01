from contextlib import nullcontext

from core import lastfm
from core.act_list import ListReport, decide_kind, import_act, merge_acts
from core.act_sources import SOURCES
from core.artist_enrichment import Matcher
from core.artist_import import rows_from_csv
from core.event_performers import link_from_names, names_to_records
from core.job_runs import RecordedCommand
from core.management.commands.enrich_artists_from_musicbrainz import Command as EnrichCommand
from core.management.commands.import_artists_from_events import named_events
from core.management.commands.sync_venues_from_gsheets import get_rows_from_google_sheets
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

"""
imports a curated list of acts as artists and bands, marking each with the list's source
(core/act_list.py has how). run as:

python manage.py import_act_list --source ohb --sheet <id> --tab "In Rotation" --tab "2026 backlog" [--dry-run] [--limit 50]
python manage.py import_act_list --source ohb --csv in-rotation.csv --csv backlog.csv

tabs are read in the order given, the first winning where two rows of one act differ. every
act becomes a record; one musicbrainz can't settle cleanly is held for review (no public page
or event links) until an editor marks it ready in the admin. afterwards every approved event
is linked to the live acts its names are. about two musicbrainz requests an act, at one a
second.
"""


class Command(RecordedCommand, BaseCommand):
    help = "import a curated list of acts as artists and bands, with their source"

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help=f"the list's key: {', '.join(SOURCES)}")
        parser.add_argument("--csv", action="append", default=[], help="a csv file of the list (repeatable)")
        parser.add_argument("--sheet", help="a google sheet's id")
        parser.add_argument("--tab", action="append", default=[], help="a tab of the sheet (repeatable, in order)")
        parser.add_argument("--limit", type=int, default=0, help="look up at most this many acts")
        parser.add_argument("--dry-run", action="store_true", help="report what would happen, and save nothing")

    def handle(self, *args, **options):
        source = options["source"]
        if source not in SOURCES:
            raise CommandError(f"unknown source {source!r}: add it to core/act_sources.py first")
        report = ListReport()
        acts = merge_acts(self.read_tabs(options), report)
        if options["limit"]:
            acts = acts[: options["limit"]]
        self.lastfm = lastfm.client() if lastfm.api_key() else None
        music_ids = MusicIds()
        matcher = Matcher(music_ids, lastfm=self)
        dry_run = options["dry_run"]
        heading = "would import" if dry_run else "importing"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} {len(acts)} acts as {source}"))
        with transaction.atomic() if dry_run else nullcontext():
            for act in acts:
                try:
                    model, mbid, reasons = decide_kind(act, matcher, music_ids)
                except MusicBrainzBusy as e:
                    self.stdout.write(self.style.WARNING(f"  {act.name}: {e}; stopping this run"))
                    break
                except MusicIdsError as e:
                    report.problems.append(f"{act.name}: {e}")
                    continue
                before = len(report.found)
                record = import_act(act, model, mbid, reasons, source, report)
                kind = type(record).__name__.lower()
                if len(report.found) > before:
                    self.stdout.write(f"  found {kind} {record.name}")
                elif record.needs_review:
                    why = ", ".join(record.REVIEW_REASONS.get(code, code) for code in reasons)
                    self.stdout.write(f"  held {kind} {record.name} ({why})")
                else:
                    self.stdout.write(f"  made {kind} {record.name}")
            report.events_linked = self.link_events()
            if dry_run:
                transaction.set_rollback(True)
        for problem in report.problems:
            self.stdout.write(self.style.WARNING(f"  {problem}"))
        self.job_summary = report.summary()
        self.stdout.write(f"\n{', '.join(f'{label} {n}' for label, n in report.summary())}")

    def read_tabs(self, options):
        if bool(options["csv"]) == bool(options["sheet"]):
            raise CommandError("give either --csv or --sheet with --tab")
        if options["csv"]:
            tabs = []
            for path in options["csv"]:
                try:
                    with open(path, newline="", encoding="utf-8-sig") as file:
                        tabs.append((path, rows_from_csv(file)))
                except OSError as e:
                    raise CommandError(f"couldn't read {path}: {e.strerror}")
            return tabs
        if not options["tab"]:
            raise CommandError("--sheet needs at least one --tab")
        return [(tab, get_rows_from_google_sheets(options["sheet"], tab)) for tab in options["tab"]]

    def link_events(self):
        """links every approved event to the records its names are; returns how many have any"""
        records = names_to_records()
        linked = 0
        for event in named_events():
            link_from_names(event, records)
            linked += event.performers.exists()
        return linked

    # the matcher's last.fm evidence, handled as the enrichment does
    artist_info = EnrichCommand.artist_info
