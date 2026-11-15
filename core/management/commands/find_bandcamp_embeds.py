import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import bandcamp_embeds
from core.bandcamp_embeds import Result, Status
from core.event_performers import rebake_events_of
from core.job_runs import RecordedCommand
from core.management.commands.check_event_sources import USER_AGENT
from core.models import Artist, Band

"""
reads the id of each artist's and band's Bandcamp player from the act's own Bandcamp page,
for the play buttons on listings and act pages (see core/bandcamp_embeds.py).

run as:

python manage.py find_bandcamp_embeds [--limit 100] [--refresh] [--dry-run]

an act is looked up when its Bandcamp address was never looked up or has changed, a year
after a player was found, or 90 days after any other result (--refresh looks up all). an act
an editor set a player for, or declined, is never requested. the page is requested politely
(robots.txt, the event checks' honest user agent, two seconds between requests, no proxy, no
javascript, no redirect off bandcamp.com); a player that was found is kept when a refresh
fails. three blocked acts in a row stop the run. only the kind and id are saved. listings of
the acts whose player changed are re-rendered, since the button is baked into them.
"""

DEFAULT_LIMIT = 100
BLOCKED_IN_A_ROW = 3
# not a problem unless a refresh failed to confirm a found player
QUIET = (Status.FOUND, Status.NO_PLAYABLE)
LABELS = ["looked up", "found", "no playable release", "failed"]


def kind_of(record):
    return "band" if isinstance(record, Band) else "artist"


def shown(record):
    """the player address the record's listings show, or "" """
    return record.bandcamp_player_url if record.bandcamp_player_usable else ""


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="look up at most this many acts")
        parser.add_argument("--refresh", action="store_true", help="look up every act with a Bandcamp page, not only those due")
        parser.add_argument("--dry-run", action="store_true", help="report what would be saved, but save nothing")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.now = timezone.now()
        self.counts = dict.fromkeys(LABELS, 0)
        self.changed = []
        records = self.records_due(options["refresh"], options["limit"])
        session = bandcamp_embeds.PoliteSession(USER_AGENT)
        heading = "would save" if self.dry_run else "saved"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(records)} acts due)"))
        blocked_in_a_row = 0
        for position, record in enumerate(records):
            try:
                result = self.look_up(session, record)
            except Exception as e:  # one act's trouble doesn't stop the run
                result = Result(Status.FAILED, why=type(e).__name__)
            if result is None:
                continue
            blocked_in_a_row = blocked_in_a_row + 1 if result.status == Status.BLOCKED else 0
            if blocked_in_a_row == BLOCKED_IN_A_ROW:
                left = len(records) - position - 1
                self.stdout.write(self.style.WARNING(f"stopped: Bandcamp blocked {BLOCKED_IN_A_ROW} acts in a row, {left} left for the next run"))
                self.job_problems.append(
                    {"venue_id": None, "sheet_id": "", "name": "run stopped: Bandcamp blocked three acts in a row", "problems": ["blocked"]}
                )
                break
        rebaked = 0 if self.dry_run else rebake_events_of(self.changed)
        self.job_summary = list(self.counts.items())
        self.stdout.write(", ".join(f"{label}: {count}" for label, count in self.counts.items()) + f"; re-rendered {rebaked} events")

    def records_due(self, refresh, limit):
        found = [
            record
            for model in (Artist, Band)
            for record in model.objects.exclude(bandcamp_url="")
            if bandcamp_embeds.due(record, self.now, refresh)
        ]
        epoch = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        found.sort(key=lambda r: (r.bandcamp_embed_checked_at or epoch, r.name))
        return found[:limit]

    def look_up(self, session, record):
        # an editor may have saved the record since the run began
        record.refresh_from_db()
        if not bandcamp_embeds.due(record, self.now, refresh=True):
            return None
        result = bandcamp_embeds.lookup(session, record.bandcamp_url)
        self.finish(record, result)
        return result

    def finish(self, record, result):
        label = f"{record.name} ({kind_of(record)})"
        kept = bandcamp_embeds.keeps_found_player(record)
        self.counts["looked up"] += 1
        if result.status == Status.FOUND:
            self.counts["found"] += 1
        elif result.status == Status.NO_PLAYABLE:
            self.counts["no playable release"] += 1
        else:
            self.counts["failed"] += 1
        if result.status not in QUIET or (result.status == Status.NO_PLAYABLE and kept):
            self.job_problems.append({"venue_id": None, "sheet_id": "", "name": label, "problems": [result.status.value]})
        fields = bandcamp_embeds.apply(record, result, self.now)
        before = shown(record)
        for name, value in fields.items():
            setattr(record, name, value)
        detail = f"{result.kind} {result.embed_id}" if result.status == Status.FOUND else result.why
        if kept and result.status != Status.FOUND:
            detail = f"{detail}; kept the player already found".strip("; ")
        self.stdout.write(f"  {label}: {result.status.value}" + (f" ({detail})" if detail else ""))
        if self.dry_run:
            return
        type(record).objects.filter(pk=record.pk).update(**fields)
        if shown(record) != before:
            self.changed.append(record)
