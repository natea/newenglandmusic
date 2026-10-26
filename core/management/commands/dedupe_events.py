from collections import defaultdict

from core.job_runs import RecordedCommand
from core.management.commands.fetch_events import normalized_title
from core.models import Event, VenueFetchStatus
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

"""
merges upcoming imported events that are copies of one show: the same venue, start time
and title (ignoring case, spaces and punctuation). fetch_events stops new copies; this
cleans up the ones saved before it did.

run as:

python manage.py dedupe_events [--dry-run]

in each group of copies, the one kept is the oldest whose source is the venue's latest
fetch source -- the daily fetch keeps that one current -- or else the oldest. it's
approved if any copy was, and takes an admin's label from another copy when it has none
of its own. the other copies are deleted. hand-entered events are never touched.
"""


def duplicate_groups():
    """lists of copies of one show, oldest first"""
    groups = defaultdict(list)
    events = (
        Event.all_objects.filter(starttime__gte=timezone.now())
        .exclude(source="")
        .exclude(venue__isnull=True)
        .select_related("venue")
        .order_by("created_at", "pk")
    )
    for event in events:
        groups[(event.venue_id, event.starttime, normalized_title(event.title))].append(event)
    return [copies for copies in groups.values() if len(copies) > 1]


def plan_merge(copies, fetch_source):
    """(the copy to keep, the copies to delete, the changes to the kept copy)"""
    current = [event for event in copies if event.source == fetch_source]
    keep = (current or copies)[0]
    others = [event for event in copies if event is not keep]
    changes = {}
    if not keep.is_approved and any(event.is_approved for event in others):
        changes["is_approved"] = True
    if keep.kind_set_by != Event.KindSetBy.ADMIN:
        labelled = [event for event in others if event.kind_set_by == Event.KindSetBy.ADMIN]
        if labelled:
            latest = max(labelled, key=lambda event: (event.created_at, event.pk))
            changes["kind"] = latest.kind
            changes["kind_set_by"] = Event.KindSetBy.ADMIN
    return keep, others, changes


def describe(event):
    approved = "approved" if event.is_approved else "unapproved"
    return f"#{event.pk} {event.source} {event.external_id} [{approved}, {event.kind or 'unlabelled'}]"


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="list what would be merged, but change nothing"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        groups = duplicate_groups()
        fetch_sources = dict(VenueFetchStatus.objects.values_list("venue_id", "source"))
        deleted = approved = relabelled = 0

        with transaction.atomic():
            for copies in sorted(groups, key=lambda copies: (copies[0].venue.name, copies[0].starttime)):
                keep, others, changes = plan_merge(copies, fetch_sources.get(copies[0].venue_id))
                when = timezone.localtime(keep.starttime).strftime("%a %b %-d %-I:%M%p")
                self.stdout.write(self.style.MIGRATE_HEADING(f"\n{keep.venue.name}, {when}: {keep.title}"))
                self.stdout.write(f"  keep    {describe(keep)}")
                for event in others:
                    self.stdout.write(f"  delete  {describe(event)}")
                if changes:
                    self.stdout.write(
                        "  then    " + ", ".join(f"{field} = {value}" for field, value in changes.items())
                    )
                approved += "is_approved" in changes
                relabelled += "kind" in changes
                deleted += len(others)
                if not dry_run:
                    Event.all_objects.filter(pk__in=[event.pk for event in others]).delete()
                    if changes:
                        for field, value in changes.items():
                            setattr(keep, field, value)
                        keep.save()

        self.job_summary = [
            ("shows with copies", len(groups)),
            ("copies deleted", deleted),
            ("kept copies approved", approved),
            ("admin labels carried over", relabelled),
        ]
        prefix = "[dry run] would delete" if dry_run else "deleted"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix} {deleted} copies of {len(groups)} shows; "
                f"{approved} kept copies approved, {relabelled} admin labels carried over"
            )
        )
