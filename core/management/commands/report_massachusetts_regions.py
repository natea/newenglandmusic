"""
reports how massachusetts's active venues fall into its sub-regions (core/geo_areas.py): each
sub-region's venue count, the venues only a county default placed (an editor may want to add
their town to a sub-region instead), and any in no sub-region. reads only; for the editors:

    venv/bin/python manage.py report_massachusetts_regions
"""

from django.core.management.base import BaseCommand

from core.geo_filters import area_q, placed_by_name_q
from core.models import GeoArea, Venue


def massachusetts_venues():
    return Venue.objects.filter(state="MA").exclude(is_active=False)


def venue_line(venue):
    place = ", ".join(part for part in (venue.city_town, venue.neighborhood) if part)
    county = f"{venue.county} county" if venue.county else "no county"
    return f"{venue.name} [{venue.sheet_id or 'no ID'}] ({place or 'no town'}; {county})"


class Command(BaseCommand):
    help = "how massachusetts's active venues fall into its sub-regions"

    def handle(self, *args, **options):
        venues = massachusetts_venues()
        by_default = set(venues.exclude(placed_by_name_q()).values_list("pk", flat=True))
        placed, defaulted = {}, {}
        self.stdout.write(f"{venues.count()} active Massachusetts venues\n")
        group = None
        for sub_region in GeoArea.objects.exclude(group=""):
            if sub_region.group != group:
                group = sub_region.group
                self.stdout.write(f"\n{group}")
            members = list(venues.filter(area_q(sub_region)).order_by("city_town", "name"))
            for venue in members:
                placed[venue.pk] = placed.get(venue.pk, 0) + 1
            defaulted[sub_region.short_label] = [venue for venue in members if venue.pk in by_default]
            self.stdout.write(f"  {len(members):4}  {sub_region.short_label}")

        self.stdout.write("\nplaced only by their county's default sub-region:")
        for label, members in defaulted.items():
            if members:
                self.stdout.write(f"\n{label} ({len(members)})")
                for venue in members:
                    self.stdout.write(f"  {venue_line(venue)}")

        unplaced = [venue for venue in venues.order_by("city_town", "name") if venue.pk not in placed]
        self.stdout.write(f"\nin no sub-region ({len(unplaced)}):")
        for venue in unplaced:
            self.stdout.write(f"  {venue_line(venue)}")
        several = [venue for venue in venues if placed.get(venue.pk, 0) > 1]
        if several:
            # the rules shouldn't allow it; say so loudly if an edit to the file does
            self.stdout.write(self.style.ERROR(f"\nin several sub-regions ({len(several)}):"))
            for venue in several:
                self.stdout.write(f"  {venue_line(venue)}")
