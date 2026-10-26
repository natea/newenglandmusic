import os

import requests
from core.event_fetching.eventbrite import (
    EventbriteClient,
    EventbriteError,
    find_eventbrite_ids,
    is_at_venue,
)
from core.job_runs import RecordedCommand
from core.management.commands.check_event_sources import (
    TIMEOUT_SECONDS,
    USER_AGENT,
    robots_allows,
)
from core.models import Venue, VenueEventSource
from django.core.management.base import BaseCommand, CommandError

"""
links venues to their eventbrite organizers, so fetch_events can get their events from
the eventbrite api.

run as:

python manage.py match_eventbrite_organizers [--sheet-ids V0198,V0026 | --all] [--recheck] [--dry-run]

by default, active venues whose saved event source (from check_event_sources) links to
eventbrite are checked; --sheet-ids checks those venues and --all every active venue.
venues that are already linked are skipped unless --recheck is given.

eventbrite has no venue search, so the organizer comes from the venue's own pages, fetched
politely as check_event_sources does: a link to its organizer page gives it directly, and
otherwise up to MAX_EVENT_LOOKUPS linked events are looked up for theirs. a venue is linked
only when its pages lead to a single organizer, and not when that organizer's live events
are all somewhere else -- a page can link another promoter's shows. needs
EVENTBRITE_API_KEY.
"""

# looking up an event's organizer costs a request; a few agreeing events are enough
MAX_EVENT_LOOKUPS = 3


def page_html(session, url):
    if not url or not robots_allows(session, url):
        return ""
    try:
        response = session.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return ""
    return response.text if response.ok else ""


def find_organizer(session, client, venue):
    """
    what the venue's pages lead to on eventbrite, as a dict: "outcome" is "found",
    "several" or "no links", with the organizer's id and its live events counted when
    there's one. raises EventbriteError
    """
    source = getattr(venue, "event_source", None)
    urls = sorted({url for url in (getattr(source, "url", ""), getattr(source, "events_page", "")) if url})
    event_ids, organizer_ids = set(), set()
    for url in urls:
        found_events, found_organizers = find_eventbrite_ids(page_html(session, url))
        event_ids |= found_events
        organizer_ids |= found_organizers
    if not organizer_ids:
        for event_id in sorted(event_ids)[:MAX_EVENT_LOOKUPS]:
            organizer_ids.add(client.event(event_id).get("organizer_id"))
        organizer_ids.discard(None)
    if not organizer_ids:
        return {"outcome": "no links", "links": len(event_ids)}
    if len(organizer_ids) > 1:
        return {"outcome": "several", "organizers": sorted(organizer_ids)}
    [organizer_id] = organizer_ids
    events = client.organizer_events(organizer_id)
    here = sum(1 for event in events if is_at_venue(event, venue))
    return {"outcome": "found", "organizer_id": organizer_id, "events": len(events), "here": here}


def eventbrite_venue_pks():
    """venues whose saved event source links to eventbrite"""
    sources = VenueEventSource.objects.all()
    if not sources.exists():
        raise CommandError(
            "no event sources saved -- run check_event_sources first, or pass --sheet-ids or --all"
        )
    return sources.filter(platforms__contains=["eventbrite"]).values("venue_id")


def polite_session():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to check")
        parser.add_argument("--all", action="store_true", help="check every active venue")
        parser.add_argument(
            "--recheck", action="store_true", help="also check venues that are already linked"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="report matches, but save nothing"
        )

    def handle(self, *args, **options):
        api_key = os.environ.get("EVENTBRITE_API_KEY")
        if not api_key:
            raise CommandError("EVENTBRITE_API_KEY is not set")

        venues = Venue.objects.select_related("event_source").order_by("sheet_id")
        if options["sheet_ids"]:
            venues = venues.filter(sheet_id__in=options["sheet_ids"].split(","))
        else:
            venues = venues.exclude(is_active=False)
            if not options["all"]:
                venues = venues.filter(pk__in=eventbrite_venue_pks())

        session = polite_session()
        client = EventbriteClient(api_key)
        groups = {
            "linked": [],
            "already linked": [],
            "several organizers": [],
            "events elsewhere": [],
            "no links": [],
            "failed": [],
        }
        for venue in venues:
            if venue.eventbrite_organizer_id and not options["recheck"]:
                groups["already linked"].append((venue, venue.eventbrite_organizer_id))
                continue
            try:
                found = find_organizer(session, client, venue)
            except EventbriteError as e:
                groups["failed"].append((venue, str(e)))
                continue

            if found["outcome"] == "several":
                groups["several organizers"].append((venue, found))
            elif found["outcome"] == "no links":
                groups["no links"].append((venue, found))
            elif found["events"] and not found["here"]:
                groups["events elsewhere"].append((venue, found))
            else:
                groups["linked"].append((venue, found))
                if not options["dry_run"]:
                    # update() rather than save(): saving a venue rebakes all its events
                    Venue.objects.filter(pk=venue.pk).update(
                        eventbrite_organizer_id=found["organizer_id"]
                    )

        self.job_summary = [(group, len(items)) for group, items in groups.items()]
        self.report(groups, options["dry_run"])

    def report(self, groups, dry_run):
        def heading(title, items):
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title} ({len(items)})"))

        def describe(venue):
            return f"{venue.sheet_id} {venue.name} ({venue.location})"

        def describe_found(found):
            return (
                f"organizer {found['organizer_id']}: {found['events']} live events, "
                f"{found['here']} at this venue"
            )

        heading("linked" + (" [dry run, not saved]" if dry_run else ""), groups["linked"])
        for venue, found in groups["linked"]:
            self.stdout.write(f"  {describe(venue)} -> {describe_found(found)}")

        heading("already linked", groups["already linked"])
        for venue, organizer_id in groups["already linked"]:
            self.stdout.write(f"  {describe(venue)} -> {organizer_id}")

        heading(
            "several organizers: set the id in the admin if one of these is right",
            groups["several organizers"],
        )
        for venue, found in groups["several organizers"]:
            self.stdout.write(f"  {describe(venue)}: {', '.join(found['organizers'])}")

        heading("events elsewhere: the organizer's live events are all at other venues", groups["events elsewhere"])
        for venue, found in groups["events elsewhere"]:
            self.stdout.write(f"  {describe(venue)}: {describe_found(found)}")

        heading("no eventbrite links on the venue's pages", groups["no links"])
        for venue, _ in groups["no links"]:
            self.stdout.write(f"  {describe(venue)}")

        if groups["failed"]:
            heading("failed", groups["failed"])
            for venue, error in groups["failed"]:
                self.stdout.write(self.style.WARNING(f"  {describe(venue)}: {error}"))
