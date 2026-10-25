import csv
import math
import os
import re

from core.event_fetching.ticketmaster import TicketmasterClient, TicketmasterError
from core.models import Venue
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
a venue is linked only when exactly one result has a matching name and lies within
MAX_DISTANCE_KM of the venue -- anything less certain is reported for an admin to settle
by setting the venue's ticketmaster venue id in the admin. needs TICKETMASTER_API_KEY.
"""

MAX_DISTANCE_KM = 1.0

# words that venues' names often gain or lose between listings
NAME_NOISE_RE = re.compile(
    r"\b(the|music hall|hall|club|theatre|theater|live|and|at)\b|presented by .*$"
)


def normalize_name(name):
    """lowercase words, without punctuation or words like "the" and "club" """
    name = name.lower().replace("&", " and ")
    name = re.sub(r"[^\w\s]", " ", name)
    words = NAME_NOISE_RE.sub(" ", " ".join(name.split()))
    return " ".join(words.split()) or " ".join(name.split())


def names_match(a, b):
    """equal, or one's words appear in a row in the other's"""
    a, b = normalize_name(a), normalize_name(b)
    return bool(a and b) and (f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(a))


def find_match(venue, candidates):
    """
    returns (outcome, match, candidates with their distances) where outcome is
    "linked", "ambiguous" or "unmatched"
    """
    scored = [
        {
            **candidate,
            "distance_km": distance_km(
                venue.latitude, venue.longitude, candidate["latitude"], candidate["longitude"]
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
    if len(near) == 1:
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
                candidates = client.search_venues(venue.name, venue.state)
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
