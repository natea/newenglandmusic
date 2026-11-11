from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from core import link_hubs
from core.job_runs import RecordedCommand
from core.management.commands.check_event_sources import USER_AGENT, robots_allows
from core.models import Artist, Band, MusicAct

"""
reads each artist's and band's link-hub page (Linktree and its rivals) and fills the links
it can recognise: website (only when the hub labels it so), Bandcamp, Instagram and YouTube.

run as:

python manage.py read_artist_link_hubs [--limit 100] [--refresh] [--dry-run]

a record is read when it has a hub address that was never read or was read over seven days
ago (--refresh reads all). a hub address in a record's website is first copied to its hub
address. the page is requested politely (robots.txt, the event checks' honest user agent,
one request a second, no javascript, no redirect off the hub's host), and nothing else is:
the links found are never requested. a link for an empty field fills it; one that differs
from the record's is saved as a finding, for an editor to review in the admin. see
core/link_hubs.py.
"""

import datetime

RECHECK_AFTER = datetime.timedelta(days=7)
DEFAULT_LIMIT = 100
Status = MusicAct.LinkHubStatus
PROBLEMS = (Status.BLOCKED, Status.GONE, Status.FAILED)
# the import marks an address copied from the website; the copy follows the website
COPIED = "import"


def hub_in_website(record):
    """the record's website as a stored hub address, or "" """
    return link_hubs.clean_hub_url(record.website)


def copy_from_website(record):
    """
    gives a record whose website is a hub address that address as its hub address (in memory):
    when it has none, or has the copy of an earlier website. an editor's or musicbrainz's
    stays. returns whether it changed
    """
    address = hub_in_website(record)
    if not address or record.link_hub_url == address:
        return False
    source = record.field_sources.get("link_hub_url")
    if record.link_hub_url and source != COPIED:
        return False
    record.link_hub_url = address
    record.field_sources["link_hub_url"] = record.field_sources.get("website") or COPIED
    return True


def candidates():
    """every record that has or may get a hub address"""
    website_is_hub = Q()
    for hub in link_hubs.HUBS:
        for host in hub.hosts:
            website_is_hub |= Q(website__icontains=host)
    for model in (Artist, Band):
        yield from model.objects.filter(Q(link_hub_url__gt="") | website_is_hub)


def due(record, now, refresh):
    if not record.link_hub_url:
        return False
    return refresh or record.link_hub_checked_at is None or record.link_hub_checked_at < now - RECHECK_AFTER


def kind_of(record):
    return "band" if isinstance(record, Band) else "artist"


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="read at most this many pages")
        parser.add_argument("--refresh", action="store_true", help="read every hub page, not only those due")
        parser.add_argument("--dry-run", action="store_true", help="report what would be recorded, but save nothing")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.now = timezone.now()
        self.counts = {"read": 0, "filled": 0, "flagged": 0, "failed": 0}
        records = self.records_due(options["refresh"], options["limit"])
        session = link_hubs.PoliteSession(USER_AGENT)
        heading = "would record" if self.dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(records)} hub pages due)"))
        for record in records:
            try:
                self.read(session, record)
            except Exception as e:  # one record's trouble doesn't stop the run
                self.finish(record, Status.FAILED, f"{type(e).__name__}")
        self.job_summary = list(self.counts.items())
        self.stdout.write(", ".join(f"{label}: {count}" for label, count in self.counts.items()))

    def records_due(self, refresh, limit):
        """copies hub addresses from websites (saved unless a dry run), then lists those due"""
        found = []
        for record in candidates():
            if copy_from_website(record) and not self.dry_run:
                type(record).objects.filter(pk=record.pk).update(
                    link_hub_url=record.link_hub_url, field_sources=record.field_sources
                )
            if due(record, self.now, refresh):
                found.append(record)
        found.sort(key=lambda r: (r.link_hub_checked_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), r.name))
        return found[:limit]

    def read(self, session, record):
        url = record.link_hub_url
        hub = link_hubs.hub_for(url)
        if hub is None:
            return self.finish(record, Status.FAILED, "not a page on a supported hub")
        if not hub.readable:
            return self.finish(record, Status.UNREADABLE, f"{hub.name} gives its links only to a browser")
        if not robots_allows(session, url):
            return self.finish(record, Status.BLOCKED, "robots.txt forbids it")
        problem, html = link_hubs.fetch(session, url)
        if problem:
            return self.finish(record, Status(problem), problem)
        found = link_hubs.links_on(html)
        if not found and link_hubs.has_script(html):
            return self.finish(record, Status.UNREADABLE, "its links are built by script")
        # an editor may have saved the record since the run began
        record.refresh_from_db()
        changes, findings = link_hubs.apply(record, found, self.now)
        usable = any(link_hubs.classify(found).values())
        self.finish(record, Status.READ if usable else Status.EMPTY, "", changes, findings)

    def finish(self, record, status, why, changes=None, findings=None):
        label = f"{record.name} ({kind_of(record)})"
        if status == Status.READ:
            self.counts["read"] += 1
        if status == Status.FAILED:
            self.counts["failed"] += 1
        if status in PROBLEMS:
            self.job_problems.append({"venue_id": None, "sheet_id": "", "name": label, "problems": [status.value]})
        changes = changes or {}
        self.counts["filled"] += len(changes)
        if findings is not None:
            self.counts["flagged"] += sum(1 for f in findings if not f["dismissed"])
        detail = ", ".join([why, *(f"{field} from the hub" for field in changes)]).strip(", ")
        self.stdout.write(f"  {label}: {status.value}" + (f" ({detail})" if detail else ""))
        if self.dry_run:
            return
        fields = {"link_hub_status": status.value, "link_hub_checked_at": self.now}
        if findings is not None:
            fields["link_hub_findings"] = findings
        if changes:
            sources = {**record.field_sources, **{field: link_hubs.LINK_HUB for field in changes}}
            fields.update(changes, field_sources=sources)
        type(record).objects.filter(pk=record.pk).update(**fields)
