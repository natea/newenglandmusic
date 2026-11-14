"""
the stored areas (GeoArea) kept in step with core/geo_areas.py after every migrate
(CoreConfig.ready), so render's build loads an edited area on deploy and a new database starts
with every area. an area is matched by its key, kept in GeoArea.sheet_id; one no longer in the
file is deleted.

to load them by hand, run any migrate:

    venv/bin/python manage.py migrate
"""

from django.utils.text import slugify

AREA_FIELDS = ("kind", "label", "home_state", "group", "states", "counties", "cities", "neighborhoods", "default_counties")


def area_fields(areas):
    """{key: GeoArea fields} for areas, in their order"""
    fields = {}
    for sort_order, area in enumerate(areas):
        fields[area["key"]] = {
            **{name: area[name] for name in AREA_FIELDS},
            "slug": slugify(area["label"]),
            "sort_order": sort_order,
        }
    return fields


def sync_geo_areas(areas=None, **kwargs):
    """makes GeoArea match areas (the file's, by default). returns (added, updated, removed)."""
    from core.geo_areas import AREAS
    from core.models import GeoArea

    wanted = area_fields(AREAS if areas is None else areas)
    existing = {area.sheet_id: area for area in GeoArea.objects.all()}
    # removed areas go first, so a new area can take a removed one's slug ((kind, slug) is unique)
    removed, _ =GeoArea.objects.exclude(sheet_id__in=wanted).delete()
    added = updated = 0
    for key, fields in wanted.items():
        area = existing.get(key)
        if area is None:
            GeoArea.objects.create(sheet_id=key, **fields)
            added += 1
        elif any(getattr(area, name) != value for name, value in fields.items()):
            GeoArea.objects.filter(pk=area.pk).update(**fields)
            updated += 1
    return added, updated, removed
