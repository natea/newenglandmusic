import os

from core.event_fetching.seatgeek import SeatGeekClient, SeatGeekError
from core.management.commands.match_ticketmaster_venues import Command as MatchTicketmasterCommand
from core.management.commands.match_ticketmaster_venues import search_names
from core.management.commands.measure_api_coverage import coverage_venues
from core.models import Venue
from core.venue_matching import find_match
from django.core.management.base import CommandError

"""
links venues to their seatgeek venues, so fetch_events can get their events from the
seatgeek api -- for venues whose ticketing pages (etix, axs) refuse our crawler.

run as:

python manage.py match_seatgeek_venues [--sheet-ids V0152,V0042 | --all] [--recheck] [--dry-run]

by default, the venues measure_api_coverage measures are checked: those whose saved event
source links eventbrite, etix or axs, and those with problems in the latest full fetch.
--sheet-ids checks those venues and --all every active venue. venues that are already
linked are skipped unless --recheck is given.

venues are matched the way match_ticketmaster_venues matches them (core/venue_matching.py),
with a search per venue: 82 venues took two minutes on 2026-10-29, so seatgeek's bulk
venues file isn't worth its download. needs SEATGEEK_CLIENT_ID.
"""


class Command(MatchTicketmasterCommand):
    def handle(self, *args, **options):
        client_id = os.environ.get("SEATGEEK_CLIENT_ID")
        if not client_id:
            raise CommandError("SEATGEEK_CLIENT_ID is not set")

        if options["sheet_ids"]:
            venues = Venue.objects.filter(sheet_id__in=options["sheet_ids"].split(",")).order_by("sheet_id")
        elif options["all"]:
            venues = Venue.objects.exclude(is_active=False).order_by("sheet_id")
        else:
            venues = coverage_venues()

        client = SeatGeekClient(client_id)
        groups = {"linked": [], "already linked": [], "ambiguous": [], "unmatched": [], "failed": []}
        for venue in venues:
            if venue.seatgeek_venue_id and not options["recheck"]:
                groups["already linked"].append((venue, venue.seatgeek_venue_id))
                continue
            try:
                candidates = search_names(client, venue)
                if not candidates and venue.city_town:
                    candidates = client.search_venues(venue.city_town, venue.state)
            except SeatGeekError as e:
                groups["failed"].append((venue, str(e)))
                continue

            outcome, match, scored = find_match(venue, candidates)
            if outcome == "linked":
                groups["linked"].append((venue, match))
                if not options["dry_run"]:
                    # update() rather than save(): saving a venue rebakes all its events
                    Venue.objects.filter(pk=venue.pk).update(seatgeek_venue_id=match["id"])
            else:
                groups[outcome].append((venue, scored))

        self.job_summary = [(group, len(items)) for group, items in groups.items()]
        self.report(groups, options["dry_run"])
