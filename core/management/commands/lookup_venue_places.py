import os

from core.models import Event, Venue
from core.places import PlacesClient, PlacesError
from core.utils_event_caching import bake_event_html
from core.venue_matching import distance_km, names_match
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

"""
looks up venues on google places, for their exact location, street address, open/closed
status and google maps link -- the sheet's coordinates are only town centres.

run as:

python manage.py lookup_venue_places [--sheet-ids V0089,V0113 | --state MA] [--limit 20] [--refresh] [--contact] [--dry-run]

each active venue is searched for by name, town and state, biased toward its sheet
coordinates. a result is a confident match only when its name matches the venue's, it's
in the venue's state, and it's within MAX_DISTANCE_KM of the sheet coordinates -- only
then is its location used (see Venue.exact_location). anything else is saved as needing
review, for an admin to confirm or clear in the venue admin.

results are kept in the venue's place_* fields, which the sheet sync never touches.
venues already looked up are skipped unless --refresh is given. permanently closed
venues are reported, but not deactivated: that's for the sheet.

cost: one request per venue. the default fields are google's "pro" tier (5,000 free
requests a month, then $32 per 1,000); --contact also gets website and phone, which are
"enterprise" tier (1,000 free a month, then $35 per 1,000). needs GOOGLE_PLACES_API_KEY.
"""

# the sheet's coordinates are town centres, so this allows for a venue across town
MAX_DISTANCE_KM = 25


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


def place_fields(status, result, contact):
    fields = {"place_lookup_status": status, "place_looked_up_at": timezone.now()}
    if result is None:
        return fields
    fields.update(
        place_id=result["id"],
        place_name=result["name"],
        place_address=result["address"],
        place_latitude=result["latitude"],
        place_longitude=result["longitude"],
        place_business_status=result["business_status"],
        place_maps_url=result["maps_url"],
    )
    if contact:
        fields.update(place_website=result["website"], place_phone=result["phone"])
    return fields


def rebake_events(venue):
    """refresh the venue's events' stored html, e.g. their map pin (see Event.save)"""
    for event in Event.all_objects.filter(venue=venue).select_related("venue"):
        Event.all_objects.filter(pk=event.pk).update(baked_html_template=bake_event_html(event))


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to look up")
        parser.add_argument("--state", help="only look up venues in this state, e.g. MA")
        parser.add_argument("--limit", type=int)
        parser.add_argument(
            "--refresh", action="store_true", help="also look up venues looked up before"
        )
        parser.add_argument(
            "--contact",
            action="store_true",
            help="also get website and phone (google's pricier enterprise tier)",
        )
        parser.add_argument("--dry-run", action="store_true", help="report, but save nothing")

    def handle(self, *args, **options):
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        if not api_key:
            raise CommandError("GOOGLE_PLACES_API_KEY is not set")

        venues = Venue.objects.order_by("sheet_id")
        if options["sheet_ids"]:
            venues = venues.filter(sheet_id__in=options["sheet_ids"].split(","))
        else:
            venues = venues.exclude(is_active=False)
        if options["state"]:
            venues = venues.filter(state=options["state"].upper())
        if not options["refresh"]:
            venues = venues.filter(place_lookup_status="")
        if options["limit"]:
            venues = venues[: options["limit"]]

        client = PlacesClient(api_key)
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
                results = client.search_place(
                    text, venue.latitude, venue.longitude, contact=options["contact"]
                )
            except PlacesError as e:
                groups["failed"].append((venue, str(e)))
                continue

            status, result, km = match_result(venue, results)
            groups[status].append((venue, result, km))
            if result and result["business_status"] == "CLOSED_PERMANENTLY":
                groups["closed"].append((venue, result, km))

            if not options["dry_run"]:
                before = (venue.exact_location, venue.google_maps_link)
                fields = place_fields(status, result, options["contact"])
                # update() rather than save(): saving a venue rebakes all its events
                Venue.objects.filter(pk=venue.pk).update(**fields)
                for name, value in fields.items():
                    setattr(venue, name, value)
                if (venue.exact_location, venue.google_maps_link) != before:
                    rebake_events(venue)

        self.report(groups, options["dry_run"])

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
            self.stdout.write(f"  {describe(venue)} -> {describe_result(result, km)}")

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
