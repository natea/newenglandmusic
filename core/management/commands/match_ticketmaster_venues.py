import csv
import os

from core.event_fetching.ticketmaster import TicketmasterClient, TicketmasterError
from core.models import Venue
from core.venue_matching import distance_km, names_match, normalize_name, spelling_variants
from django.core.management.base import BaseCommand, CommandError

"""
links venues to their ticketmaster venues, so fetch_events can get their events from the
ticketmaster discovery api.

run as:

python manage.py match_ticketmaster_venues [--report event_sources.csv] [--sheet-ids V0089,V0113 | --all] [--recheck] [--dry-run]

by default, active venues whose event-source report (from check_event_sources) lists
ticketmaster or live nation are checked; --sheet-ids checks those venues and --all every
active venue. venues that are already linked are skipped unless --recheck is given.

each venue's name is searched for in its state (and, when that finds nothing, its city).
only results with a matching name within MAX_DISTANCE_KM of the venue count (its google
places location when confident -- see lookup_venue_places). of those, the one with the
venue's own name is linked, or the only one when none has it exactly -- anything less
certain is reported for an admin to settle by setting the venue's ticketmaster venue id
in the admin. needs TICKETMASTER_API_KEY.
"""

MAX_DISTANCE_KM = 1.0

def find_match(venue, candidates):
    """
    returns (outcome, match, candidates with their distances) where outcome is
    "linked", "ambiguous" or "unmatched"
    """
    scored = [
        {
            **candidate,
            # the google places location when it's a confident match; the sheet's own
            # coordinates are only town centres
            "distance_km": distance_km(
                *venue.exact_location, candidate["latitude"], candidate["longitude"]
            ),
        }
        for candidate in candidates
    ]
    if not scored:
        return "unmatched", None, scored
    near = [
        c
        for c in scored
        if names_match(venue.name, c["name"])
        and c["distance_km"] is not None
        and c["distance_km"] <= MAX_DISTANCE_KM
    ]
    # prefer a listing with the venue's own name over ones that merely contain it,
    # e.g. "Big Night Live" over "PLAY Boston at Big Night Live"
    exact = [c for c in near if normalize_name(c["name"]) == normalize_name(venue.name)]
    if len(exact) == 1:
        return "linked", exact[0], scored
    if not exact and len(near) == 1:
        return "linked", near[0], scored
    return "ambiguous", None, scored


def ticketmaster_sheet_ids(report_path):
    try:
        with open(report_path) as f:
            return {
                row["sheet_id"]
                for row in csv.DictReader(f)
                if "ticketmaster" in row["platforms"].split(";")
            }
    except FileNotFoundError:
        raise CommandError(
            f"{report_path} not found -- run check_event_sources first, or pass --sheet-ids or --all"
        )



def search_names(client, venue):
    """candidates for each spelling of the venue's name, without repeats"""
    candidates = {}
    for name in spelling_variants(venue.name):
        for candidate in client.search_venues(name, venue.state):
            candidates.setdefault(candidate["id"], candidate)
    return list(candidates.values())

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--report", default="event_sources.csv")
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to check")
        parser.add_argument("--all", action="store_true", help="check every active venue")
        parser.add_argument(
            "--recheck", action="store_true", help="also check venues that are already linked"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="report matches, but save nothing"
        )

    def handle(self, *args, **options):
        api_key = os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            raise CommandError("TICKETMASTER_API_KEY is not set")

        venues = Venue.objects.order_by("sheet_id")
        if options["sheet_ids"]:
            venues = venues.filter(sheet_id__in=options["sheet_ids"].split(","))
        else:
            venues = venues.exclude(is_active=False)
            if not options["all"]:
                venues = venues.filter(sheet_id__in=ticketmaster_sheet_ids(options["report"]))

        client = TicketmasterClient(api_key)
        groups = {"linked": [], "already linked": [], "ambiguous": [], "unmatched": [], "failed": []}
        for venue in venues:
            if venue.ticketmaster_venue_id and not options["recheck"]:
                groups["already linked"].append((venue, venue.ticketmaster_venue_id))
                continue
            try:
                candidates = search_names(client, venue)
                if not candidates and venue.city_town:
                    candidates = client.search_venues(venue.city_town, venue.state)
            except TicketmasterError as e:
                groups["failed"].append((venue, str(e)))
                continue

            outcome, match, scored = find_match(venue, candidates)
            if outcome == "linked":
                groups["linked"].append((venue, match))
                if not options["dry_run"]:
                    # update() rather than save(): saving a venue rebakes all its events
                    Venue.objects.filter(pk=venue.pk).update(ticketmaster_venue_id=match["id"])
            else:
                groups[outcome].append((venue, scored))

        self.report(groups, options["dry_run"])

    def report(self, groups, dry_run):
        def heading(title, items):
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title} ({len(items)})"))

        def describe(venue):
            return f"{venue.sheet_id} {venue.name} ({venue.location})"

        def describe_candidate(c):
            distance = "no coordinates" if c["distance_km"] is None else f"{c['distance_km']:.2f} km"
            return f"{c['id']}  {c['name']}, {c['address']}, {c['city']} [{distance}]"

        heading("linked" + (" [dry run, not saved]" if dry_run else ""), groups["linked"])
        for venue, match in groups["linked"]:
            self.stdout.write(f"  {describe(venue)} -> {describe_candidate(match)}")

        heading("already linked", groups["already linked"])
        for venue, ticketmaster_id in groups["already linked"]:
            self.stdout.write(f"  {describe(venue)} -> {ticketmaster_id}")

        heading("ambiguous: set the id in the admin if one of these is right", groups["ambiguous"])
        for venue, candidates in groups["ambiguous"]:
            self.stdout.write(f"  {describe(venue)}")
            for candidate in candidates:
                self.stdout.write(f"      {describe_candidate(candidate)}")

        heading("unmatched", groups["unmatched"])
        for venue, _ in groups["unmatched"]:
            self.stdout.write(f"  {describe(venue)}")

        if groups["failed"]:
            heading("failed", groups["failed"])
            for venue, error in groups["failed"]:
                self.stdout.write(self.style.WARNING(f"  {describe(venue)}: {error}"))
