import datetime
import os

from core.job_runs import RecordedCommand
from core.models import Event, Venue
from core.places import PlaceNotFound, PlacesClient, PlacesError
from core.utils_event_caching import bake_event_html
from core.venue_matching import distance_km, names_match
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

"""
looks up venues on google places, for their exact location -- the sheet's coordinates are
only town centres -- and keeps those coordinates fresh within google's terms.

run as:

python manage.py lookup_venue_places [--sheet-ids V0089,V0113 | --state MA] [--limit 20] [--refresh] [--dry-run]
python manage.py lookup_venue_places --refresh-stale [--max-age-days 25] [--dry-run]
python manage.py lookup_venue_places --review [--state MA] [--limit 20] [--dry-run]

each active venue is searched for by name, town and state, biased toward its sheet
coordinates. a result is a confident match only when its name matches the venue's, it's
in the venue's state, and it's within MAX_DISTANCE_KM of the sheet coordinates -- only
then is its location used (see Venue.exact_location). anything else is saved as needing
review, for an admin to confirm or clear in the venue admin, with the checks it failed
(name, state, distance) and its distance, so the admin can say why. --review searches again
only for venues needing review, to record those reasons for ones looked up before. venues already looked up are
skipped unless --refresh is given.

google's terms allow storing only the place id (indefinitely) and its coordinates (for
30 days), so that's all that's saved; the result's name, address and open/closed status
are used while the run lasts, to judge the match and report permanently closed venues
(for the sheet to mark inactive).

--refresh-stale re-fetches, by place id (place details, not a new search), the
coordinates of venues fetched more than --max-age-days ago (25). run it daily and each
venue is refreshed about every 25 days. every run then deletes coordinates fetched more
than 30 days ago -- even when its requests fail or the key is missing -- and the venue
falls back to its sheet coordinates until a refresh succeeds. a place id google no longer
knows is cleared, so the next plain run searches for the venue again.

cost: one request per venue. a search uses google's "pro" fields, and a refresh only id,
location and business status (place details pro): 5,000 free requests a month for each
of the two, after which they're billed (see google's pricing page). refreshing ~730
venues every 25 days is ~880 requests a month. needs GOOGLE_PLACES_API_KEY.
"""

# the sheet's coordinates are town centres, so this allows for a venue across town
MAX_DISTANCE_KM = 25
# google's terms: coordinates may be cached for up to 30 consecutive days
COORDINATE_MAX_AGE_DAYS = 30
# refreshing before then leaves room for a few failed daily runs
DEFAULT_MAX_AGE_DAYS = 25
CLOSED = "CLOSED_PERMANENTLY"


def match_result(venue, results):
    """returns (status, the result to save or None, its distance from the venue in km)"""
    if not results:
        return Venue.PlaceLookupStatus.NOT_FOUND, None, None

    def distance(result):
        return distance_km(venue.latitude, venue.longitude, result["latitude"], result["longitude"])

    for result in results:
        km = distance(result)
        nearby = venue.latitude is None or (km is not None and km <= MAX_DISTANCE_KM)
        if names_match(venue.name, result["name"]) and result["state"] == venue.state and nearby:
            return Venue.PlaceLookupStatus.CONFIDENT, result, km
    return Venue.PlaceLookupStatus.REVIEW, results[0], distance(results[0])


def review_reasons(venue, result, km):
    """
    the checks a result failed, in a fixed order: "name" (it isn't the venue's name),
    "state" (it's in another state), "distance" (it's over MAX_DISTANCE_KM away). our own
    judgment of the match, kept so the admin can say why a venue needs review
    """
    reasons = []
    if not names_match(venue.name, result["name"]):
        reasons.append("name")
    if result["state"] != venue.state:
        reasons.append("state")
    if venue.latitude is not None and (km is None or km > MAX_DISTANCE_KM):
        reasons.append("distance")
    return reasons


def place_fields(status, result, venue=None, km=None):
    """
    only what google's terms let us keep: the place id and its coordinates, plus, for a
    match needing review, which checks it failed and its distance (deleted with the
    coordinates)
    """
    fields = {
        "place_lookup_status": status,
        "place_looked_up_at": timezone.now(),
        "place_review_reasons": [],
        "place_distance_km": None,
    }
    if status == Venue.PlaceLookupStatus.REVIEW and result is not None and venue is not None:
        fields["place_review_reasons"] = review_reasons(venue, result, km)
        fields["place_distance_km"] = None if km is None else round(km, 1)
    if result is None:
        return fields
    fields.update(
        place_id=result["id"],
        place_latitude=result["latitude"],
        place_longitude=result["longitude"],
    )
    return fields


CLEARED_LOOKUP = {
    "place_lookup_status": "",
    "place_looked_up_at": None,
    "place_id": "",
    "place_latitude": None,
    "place_longitude": None,
    "place_review_reasons": [],
    "place_distance_km": None,
}


def rebake_events(venue):
    """refresh the venue's events' stored html, e.g. their map pin (see Event.save)"""
    for event in Event.all_objects.filter(venue=venue).select_related("venue"):
        Event.all_objects.filter(pk=event.pk).update(baked_html_template=bake_event_html(event))


def save_venue(venue, fields):
    """
    saves place fields with update() -- venue.save() would rebake every event -- and
    rebakes the events only when the venue's location or map link actually changed
    """
    before = (venue.exact_location, venue.google_maps_link)
    Venue.objects.filter(pk=venue.pk).update(**fields)
    for name, value in fields.items():
        setattr(venue, name, value)
    if (venue.exact_location, venue.google_maps_link) != before:
        rebake_events(venue)


def coordinates_to_expire():
    cutoff = timezone.now() - datetime.timedelta(days=COORDINATE_MAX_AGE_DAYS)
    return Venue.objects.filter(place_looked_up_at__lt=cutoff, place_latitude__isnull=False)


def expire_stale_coordinates(dry_run=False):
    """
    deletes coordinates fetched more than 30 days ago, keeping the place id and status
    so a later refresh can restore them. returns the venues
    """
    venues = list(coordinates_to_expire().order_by("sheet_id"))
    if not dry_run:
        for venue in venues:
            # the distance comes from google's coordinates, so it goes with them
            save_venue(venue, {"place_latitude": None, "place_longitude": None, "place_distance_km": None})
    return venues


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to look up")
        parser.add_argument("--state", help="only look up venues in this state, e.g. MA")
        parser.add_argument("--limit", type=int)
        parser.add_argument(
            "--refresh", action="store_true", help="also look up venues looked up before"
        )
        parser.add_argument(
            "--review",
            action="store_true",
            help="search again only for venues needing review, to record why (a one-off backfill)",
        )
        parser.add_argument(
            "--refresh-stale",
            action="store_true",
            help="re-fetch, by place id, coordinates older than --max-age-days",
        )
        parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
        parser.add_argument("--dry-run", action="store_true", help="report, but save nothing")

    def handle(self, *args, **options):
        self.job_summary = []
        try:
            api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
            if not api_key:
                raise CommandError("GOOGLE_PLACES_API_KEY is not set")
            client = PlacesClient(api_key)
            if options["refresh_stale"]:
                self.refresh_stale(client, options)
            else:
                self.look_up(client, options)
        finally:
            # whatever happened above, coordinates past google's 30 days go
            expired = expire_stale_coordinates(options["dry_run"])
            self.job_summary.append(("coordinates expired", len(expired)))
            self.report_expired(expired, options["dry_run"])

    def selected_venues(self, options):
        venues = Venue.objects.order_by("sheet_id")
        if options["sheet_ids"]:
            venues = venues.filter(sheet_id__in=options["sheet_ids"].split(","))
        else:
            venues = venues.exclude(is_active=False)
        if options["state"]:
            venues = venues.filter(state=options["state"].upper())
        return venues

    def look_up(self, client, options):
        venues = self.selected_venues(options)
        if options["review"]:
            # a one-off: search again for venues needing review, so they get their reasons
            venues = venues.filter(place_lookup_status=Venue.PlaceLookupStatus.REVIEW)
        elif not options["refresh"]:
            venues = venues.filter(place_lookup_status="")
        if options["limit"]:
            venues = venues[: options["limit"]]

        groups = {status: [] for status in Venue.PlaceLookupStatus.values}
        groups["closed"] = []
        groups["failed"] = []
        venues = list(venues)
        self.stdout.write(f"looking up {len(venues)} venues...")
        for i, venue in enumerate(venues, start=1):
            if i % 50 == 0:
                self.stdout.write(f"  {i}/{len(venues)}")
                self.stdout.flush()
            text = ", ".join(part for part in (venue.name, venue.city_town, venue.state) if part)
            try:
                results = client.search_place(text, venue.latitude, venue.longitude)
            except PlacesError as e:
                groups["failed"].append((venue, str(e)))
                continue

            status, result, km = match_result(venue, results)
            groups[status].append((venue, result, km))
            if result and result["business_status"] == CLOSED:
                groups["closed"].append((venue, result, km))
            if not options["dry_run"]:
                save_venue(venue, place_fields(status, result, venue, km))

        self.job_summary = [(group, len(items)) for group, items in groups.items()]
        self.report(groups, options["dry_run"])

    def refresh_stale(self, client, options):
        cutoff = timezone.now() - datetime.timedelta(days=options["max_age_days"])
        venues = (
            self.selected_venues(options)
            .exclude(place_id="")
            .filter(place_looked_up_at__lt=cutoff)
        )
        if options["limit"]:
            venues = venues[: options["limit"]]
        venues = list(venues)
        self.stdout.write(
            f"refreshing {len(venues)} venues whose coordinates are over "
            f"{options['max_age_days']} days old..."
        )
        groups = {"refreshed": [], "gone": [], "closed": [], "failed": []}
        for venue in venues:
            try:
                place = client.place_details(venue.place_id)
            except PlaceNotFound:
                groups["gone"].append((venue, ""))
                if not options["dry_run"]:
                    save_venue(venue, CLEARED_LOOKUP)
                continue
            except PlacesError as e:
                groups["failed"].append((venue, str(e)))
                continue
            groups["refreshed"].append((venue, ""))
            if place["business_status"] == CLOSED:
                groups["closed"].append((venue, ""))
            if not options["dry_run"]:
                # the match status stays as it is: an admin's confirmation survives
                save_venue(
                    venue,
                    {
                        "place_id": place["id"],
                        "place_latitude": place["latitude"],
                        "place_longitude": place["longitude"],
                        "place_looked_up_at": timezone.now(),
                    },
                )

        self.job_summary = [(group, len(items)) for group, items in groups.items()]
        suffix = " [dry run, not saved]" if options["dry_run"] else ""
        titles = {
            "refreshed": "refreshed" + suffix,
            "gone": "no longer on google: lookup cleared, so the next run searches again" + suffix,
            "closed": "permanently closed: mark inactive in the sheet",
            "failed": "failed: kept until its coordinates are 30 days old",
        }
        for group, items in groups.items():
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{titles[group]} ({len(items)})"))
            for venue, error in items:
                line = f"  {venue.sheet_id} {venue.name} ({venue.location})" + (
                    f": {error}" if error else ""
                )
                warn = group in ("closed", "failed", "gone")
                self.stdout.write(self.style.WARNING(line) if warn else line)

    def report_expired(self, venues, dry_run):
        title = "coordinates over 30 days old" + (
            ": would be deleted [dry run]" if dry_run else ": deleted, using sheet coordinates"
        )
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title} ({len(venues)})"))
        for venue in venues:
            self.stdout.write(f"  {venue.sheet_id} {venue.name} ({venue.location})")

    def report(self, groups, dry_run):
        def heading(title, items):
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title} ({len(items)})"))

        def describe(venue):
            return f"{venue.sheet_id} {venue.name} ({venue.location})"

        def describe_result(result, km):
            distance = "" if km is None else f" [{km:.1f} km from the sheet's coordinates]"
            return f"{result['name']}, {result['address']}{distance}"

        suffix = " [dry run, not saved]" if dry_run else ""
        heading("confident" + suffix, groups["confident"])
        for venue, result, km in groups["confident"]:
            self.stdout.write(f"  {describe(venue)} -> {describe_result(result, km)}")

        heading("needs review: confirm or clear in the venue admin" + suffix, groups["review"])
        for venue, result, km in groups["review"]:
            why = ", ".join(review_reasons(venue, result, km)) or "-"
            self.stdout.write(f"  {describe(venue)} -> {describe_result(result, km)} [failed: {why}]")

        heading("not found" + suffix, groups["not_found"])
        for venue, _, _ in groups["not_found"]:
            self.stdout.write(f"  {describe(venue)}")

        heading("permanently closed: mark inactive in the sheet", groups["closed"])
        for venue, result, km in groups["closed"]:
            self.stdout.write(self.style.WARNING(f"  {describe(venue)} -> {describe_result(result, km)}"))

        if groups["failed"]:
            heading("failed", groups["failed"])
            for venue, error in groups["failed"]:
                self.stdout.write(self.style.WARNING(f"  {describe(venue)}: {error}"))
