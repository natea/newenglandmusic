"""
the venue list as csv rows, for the admin's "Export to CSV" button (VenueAdmin.export_csv_view).

the columns are listed by hand, never "every field", so a new Venue field isn't handed out by
accident: test_venue_export fails until a new field is exported or named in NOT_EXPORTED.
google's coordinates (and what's worked out from them) are never exported, because google's
terms keep them for only 30 days and a file outlives that.
"""
from .models import Venue

VENUE_COLUMNS = [
    "sheet_id", "name", "is_active", "venue_type", "size",
    "state", "city_town", "county", "latitude", "longitude",
    "genres", "genre_notes", "niche_notes",
    "open_booking", "booking_type", "open_mic", "website", "booking_url", "booking_notes",
    "age_policy", "accessibility_notes", "family_friendly", "lgbtq_friendly", "diverse",
    "safety_flag", "safety_url", "safety_notes",
    "neighborhood", "neighborhood_source",
    "ticketmaster_venue_id", "eventbrite_organizer_id", "seatgeek_venue_id", "ticket_page_url",
    "place_id", "place_lookup_status", "place_review_reasons",
]

# columns from the saved event-source check (VenueEventSource), blank for a venue never checked
SOURCE_COLUMNS = {
    "best_source": "best_source",
    "events_page": "events_page",
    "calendar_feed_url": "ical_url",
    "ticketing_platforms": "platforms",
    "source_checked_at": "checked_at",
}

HEADER = [*VENUE_COLUMNS, *SOURCE_COLUMNS]

# Venue fields left out on purpose, each needing a reason: add new fields to the columns or here
NOT_EXPORTED = {
    "id",
    # from google, which lets us keep the coordinates for 30 days only
    "place_latitude",
    "place_longitude",
    "place_distance_km",
    "place_looked_up_at",
    # bookkeeping, not a detail of the venue
    "neighborhood_checked_at",
}

# a cell starting with one of these could run as a formula when the file is opened
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def guard(value):
    """text that starts like a formula gets an apostrophe, so a spreadsheet shows it as text"""
    if isinstance(value, str) and value.startswith(FORMULA_STARTS):
        return "'" + value
    return value


def cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return guard("; ".join(str(item) for item in value))
    if isinstance(value, (int, float)):
        # the sheet's coordinates stay numbers, so a negative longitude isn't altered
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return guard(str(value))


def venue_row(venue):
    row = [cell(getattr(venue, name)) for name in VENUE_COLUMNS]
    try:
        source = venue.event_source
    except Venue.event_source.RelatedObjectDoesNotExist:
        source = None
    row += [cell(getattr(source, name)) if source else "" for name in SOURCE_COLUMNS.values()]
    return row
