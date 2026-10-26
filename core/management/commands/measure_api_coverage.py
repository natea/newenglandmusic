import os

from core.event_fetching.eventbrite import EventbriteClient, EventbriteError
from core.job_runs import RecordedCommand
from core.management.commands.match_eventbrite_organizers import find_organizer, polite_session
from core.models import JobRun, Venue, VenueEventSource
from django.core.management.base import BaseCommand

"""
measures how many of the venues whose events we can't fetch well the eventbrite (and,
once it has a key, seatgeek) api could cover -- before building the full import. saves
nothing.

run as:

python manage.py measure_api_coverage [--sheet-ids V0026,V0142]

by default it checks the venues with problems in the latest full fetch_events run, and
every venue whose pages link eventbrite, etix or axs. for eventbrite, the organizer is
found the way match_eventbrite_organizers finds it, and its live events are counted, with
how many of them are at this venue.
"""

PLATFORMS = ["eventbrite", "etix", "axs"]


def coverage_venues(sheet_ids=None):
    venues = Venue.objects.select_related("event_source").exclude(is_active=False)
    if sheet_ids:
        return list(venues.filter(sheet_id__in=sheet_ids).order_by("sheet_id"))
    full_fetch = (
        JobRun.objects.filter(command="fetch_events", arguments__all=True, dry_run=False)
        .order_by("-started_at")
        .first()
    )
    problem_ids = {p["venue_id"] for p in (full_fetch.problems if full_fetch else [])}
    platform_ids = set(
        VenueEventSource.objects.filter(platforms__overlap=PLATFORMS).values_list(
            "venue_id", flat=True
        )
    )
    return list(venues.filter(pk__in=problem_ids | platform_ids).order_by("sheet_id"))


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to measure instead")

    def handle(self, *args, **options):
        sheet_ids = options["sheet_ids"].split(",") if options["sheet_ids"] else None
        venues = coverage_venues(sheet_ids)
        self.stdout.write(f"measuring api coverage for {len(venues)} venues...")
        self.session = polite_session()

        api_key = os.environ.get("EVENTBRITE_API_KEY")
        self.eventbrite = EventbriteClient(api_key) if api_key else None
        if not self.eventbrite:
            self.stdout.write(self.style.WARNING("eventbrite: skipped (no EVENTBRITE_API_KEY)"))
        if not os.environ.get("SEATGEEK_CLIENT_ID"):
            self.stdout.write(self.style.WARNING("seatgeek: skipped (no SEATGEEK_CLIENT_ID)"))

        counts = {"organizer found": 0, "with events here": 0, "events here": 0}
        for venue in venues:
            outcome = self.measure_eventbrite(venue) if self.eventbrite else None
            if outcome and outcome.get("outcome") == "found":
                counts["organizer found"] += 1
                if outcome["here"]:
                    counts["with events here"] += 1
                    counts["events here"] += outcome["here"]
            self.report(venue, outcome)

        self.job_summary = [("venues", len(venues)), *counts.items()]
        self.stdout.write(
            self.style.SUCCESS(
                f"\neventbrite: organizer found for {counts['organizer found']} of {len(venues)} venues; "
                f"{counts['with events here']} have upcoming events there ({counts['events here']} events)"
            )
        )

    def measure_eventbrite(self, venue):
        """what eventbrite offers for this venue, as a dict for the report"""
        try:
            return find_organizer(self.session, self.eventbrite, venue)
        except EventbriteError as e:
            return {"error": str(e)}

    def report(self, venue, outcome):
        platforms = ", ".join(getattr(getattr(venue, "event_source", None), "platforms", []) or [])
        heading = f"{venue.sheet_id} {venue.name} ({venue.city_town}, {venue.state})"
        self.stdout.write(f"{heading} [{platforms or 'no platforms'}]")
        if outcome is None:
            return
        if "error" in outcome:
            self.stdout.write(self.style.WARNING(f"  eventbrite failed: {outcome['error']}"))
        elif outcome["outcome"] == "found":
            self.stdout.write(
                f"  eventbrite organizer {outcome['organizer_id']}: {outcome['events']} live events, "
                f"{outcome['here']} at this venue"
            )
        elif outcome["outcome"] == "several":
            self.stdout.write(f"  eventbrite: several organizers {', '.join(outcome['organizers'])}")
        else:
            self.stdout.write("  eventbrite: no links found on the venue's pages")
