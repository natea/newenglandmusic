import datetime

from core.job_runs import RecordedCommand
from core.models import Event, Venue
from core.neighborhoods import (
    NominatimBlocked,
    has_point_neighborhoods,
    OsmClient,
    OsmError,
    OverpassUnavailable,
    accepted_result,
    choose_name,
)
from core.utils_event_caching import bake_event_html
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

"""
finds each venue's neighborhood on openstreetmap, for the events' "Boston (West End)" and the
neighborhood filter.

run as:

python manage.py lookup_venue_neighborhoods [--sheet-ids V0089,V0113 | --state MA] [--limit 300] [--dry-run]

each due venue is searched for on nominatim by its own name, town and state; a result counts
only when its name is the venue's and it's in the venue's town and state. its address names
the neighborhood (see core/neighborhoods.py for which name is chosen); in new york and dc,
where openstreetmap marks neighborhoods only as points, overpass finds the nearest one. no google data is sent anywhere.

a venue is due when it was never looked up or was looked up over RECHECK_AFTER ago, unless
an editor set its neighborhood. nominatim refusing us stops the run, keeping what it found;
overpass staying busy leaves that venue due for the next run.
"""

RECHECK_AFTER = datetime.timedelta(days=365)
DEFAULT_LIMIT = 300
Source = Venue.NeighborhoodSource


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-ids", help="comma-separated Venue_IDs to look up, due or not")
        parser.add_argument("--state", help="only venues in this state, e.g. MA")
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="look up at most this many venues")
        parser.add_argument("--dry-run", action="store_true", help="report what would be recorded, but save nothing")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.now = timezone.now()
        self.counts = {
            "looked up": 0, "found": 0, "from the address": 0, "from overpass": 0,
            "found, no neighborhood": 0, "not on openstreetmap": 0, "failed": 0, "left for the next run": 0,
        }
        venues = Venue.objects.filter(is_active=True).exclude(city_town="").exclude(state="").exclude(
            neighborhood_source=Source.EDITOR
        )
        if options["state"]:
            venues = venues.filter(state=options["state"].upper())
        if options["sheet_ids"]:
            venues = venues.filter(sheet_id__in=[s.strip() for s in options["sheet_ids"].split(",") if s.strip()])
        else:
            venues = venues.filter(
                Q(neighborhood_checked_at__isnull=True) | Q(neighborhood_checked_at__lt=self.now - RECHECK_AFTER)
            )
        venues = list(venues.order_by("state", "city_town", "name")[: options["limit"]])
        osm = OsmClient()

        heading = "would record" if self.dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(venues)} venues due)"))
        stopped = ""
        for index, venue in enumerate(venues):
            try:
                found = self.look_up(osm, venue)
            except NominatimBlocked as e:
                self.counts["failed"] += 1
                self.counts["left for the next run"] += len(venues) - index
                stopped = str(e)
                self.stdout.write(self.style.WARNING(f"  {venue.name}: {e}; stopping this run"))
                break
            except OverpassUnavailable as e:
                self.counts["left for the next run"] += 1
                self.stdout.write(self.style.WARNING(f"  {venue.name}: {e}; left for the next run"))
                continue
            except OsmError as e:
                self.counts["failed"] += 1
                self.stdout.write(self.style.WARNING(f"  {venue.name}: failed: {e}"))
                continue
            self.record(venue, *found)

        self.job_summary = list(self.counts.items())
        if stopped:
            self.stdout.write(self.style.WARNING(f"stopped early, {self.counts['left for the next run']} venues left: {stopped}"))

    def look_up(self, osm, venue):
        """(neighborhood, source, report label); raises OsmError when a service can't be asked"""
        self.counts["looked up"] += 1
        result = accepted_result(osm.search(venue.name, venue.city_town, venue.state), venue.name, venue.city_town, venue.state)
        if result is None:
            return "", Source.NONE, "not on openstreetmap"
        self.counts["found"] += 1
        name = choose_name(result.get("address") or {}, venue.city_town)
        if name:
            return name, Source.ADDRESS, "from the address"
        # neighborhoods mapped only as points (new york, dc) aren't in any address
        if has_point_neighborhoods(venue.city_town, venue.state):
            name = osm.nearest_neighborhood(float(result["lat"]), float(result["lon"]), venue.city_town)
            if name:
                return name, Source.OVERPASS, "from overpass"
        return "", Source.NONE, "found, no neighborhood"

    def record(self, venue, neighborhood, source, label):
        self.counts[label] += 1
        self.stdout.write(f"  {venue.name} ({venue.city_town}, {venue.state}): {neighborhood or '-'} ({label})")
        if self.dry_run:
            return
        changed = neighborhood != venue.neighborhood
        # update(), not save(): only venues whose neighborhood changed are re-rendered below
        Venue.objects.filter(pk=venue.pk).update(
            neighborhood=neighborhood, neighborhood_source=source, neighborhood_checked_at=self.now
        )
        if changed:
            venue.neighborhood = neighborhood
            rerender_upcoming_events(venue)


def rerender_upcoming_events(venue):
    """re-bake the venue's upcoming events, whose stored html shows its neighborhood"""
    for event in Event.all_objects.filter(venue=venue, starttime__gte=timezone.now()).select_related("venue"):
        event.venue = venue
        Event.all_objects.filter(pk=event.pk).update(baked_html_template=bake_event_html(event))
