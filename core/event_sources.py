"""
saving and reading check_event_sources' results (VenueEventSource).

a result is a dict in the old event_sources.csv's shape -- platforms ";"-joined, js_heavy
"yes" or "", counts as numbers or strings -- whether it comes from the check itself or
from a csv row, so the check, the csv import and csv export all share these helpers.
"""

from core.models import VenueEventSource
from django.utils import timezone

# the old report file's columns, in its order
CSV_COLUMNS = [
    "sheet_id",
    "name",
    "state",
    "city_town",
    "url",
    "events_page",
    "best_source",
    "json_ld_events",
    "ical_url",
    "ical_events",
    "platforms",
    "js_heavy",
    "error",
]

URL_MAX_LENGTH = 1000


def _url(value):
    # a url too long for the column is no use to the readers, so drop it
    value = (value or "").strip()
    return value if len(value) <= URL_MAX_LENGTH else ""


def _count(value):
    if value in (None, ""):
        return None
    return int(value)


def save_event_source(venue, result, checked_at=None):
    """
    saves one check result as the venue's event source, replacing any earlier one.
    never calls Venue.save(), so the venue's events aren't re-rendered
    """
    platforms = result.get("platforms") or ""
    if isinstance(platforms, str):
        platforms = [p for p in platforms.split(";") if p]
    source, _ = VenueEventSource.objects.update_or_create(
        venue=venue,
        defaults={
            "checked_at": checked_at or timezone.now(),
            "url": _url(result.get("url")),
            "events_page": _url(result.get("events_page")),
            "best_source": result["best_source"],
            "json_ld_events": _count(result.get("json_ld_events")) or 0,
            "ical_url": _url(result.get("ical_url")),
            "ical_events": _count(result.get("ical_events")),
            "platforms": sorted(platforms),
            "js_heavy": result.get("js_heavy") in (True, "yes"),
            "error": result.get("error") or "",
        },
    )
    return source


def event_source_row(source):
    """the row dict that fetch_events' venue selection reads"""
    return {
        "sheet_id": source.venue.sheet_id,
        "url": source.url,
        "events_page": source.events_page,
        "best_source": source.best_source,
        "json_ld_events": source.json_ld_events,
        "ical_url": source.ical_url,
        "platforms": source.platforms,
        "js_heavy": source.js_heavy,
    }


def event_source_csv_row(source):
    """the source as a row of the old report file, for people to read"""
    venue = source.venue
    return {
        "sheet_id": venue.sheet_id or "",
        "name": venue.name,
        "state": venue.state,
        "city_town": venue.city_town,
        "url": source.url,
        "events_page": source.events_page,
        "best_source": source.best_source,
        "json_ld_events": source.json_ld_events,
        "ical_url": source.ical_url,
        "ical_events": "" if source.ical_events is None else source.ical_events,
        "platforms": ";".join(source.platforms),
        "js_heavy": "yes" if source.js_heavy else "",
        "error": source.error,
    }
