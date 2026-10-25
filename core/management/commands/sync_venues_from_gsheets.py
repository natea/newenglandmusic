import json
import subprocess

from core.models import Venue
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

"""
syncs venues from the "Northeastern US Music Venues" google sheet into the db.

run as:

python manage.py sync_venues_from_gsheets [--dry-run]

the sheet is read with the gog cli, which must be installed and authorized
with the sheets service.

every row must have a Venue_ID (e.g. V0042) -- venues are matched on it, so it
must never change for a given row. rows are created or updated; venues that are
no longer in the sheet are reported but never deleted.
"""

DEFAULT_SHEET_ID = "1QBzKHOUWOR0Fw0ODrwEep5eGfZg4SmTUq4PsaCbbnGQ"
DEFAULT_TAB = "V3 - Flattened"

BOOKING_TYPES_BY_LABEL = {
    label.lower(): value for value, label in Venue.BookingType.choices
}


def parse_yes_no(value):
    """'Y' -> True, 'N' -> False, anything else (blank, 'Maybe?', '???') -> None"""
    value = value.strip().upper()
    if value in ("Y", "YES"):
        return True
    if value in ("N", "NO"):
        return False
    return None


def parse_float(value):
    try:
        return float(value)
    except ValueError:
        return None


def parse_size(value):
    # sheet values look like "Small (<100)"
    value = value.strip().lower()
    for size in Venue.Size.values:
        if value.startswith(size):
            return size
    return ""


def parse_genres(value):
    # sheet values look like "Funk; Jazz;" or "ALL"
    return [genre.strip() for genre in value.split(";") if genre.strip()]


def venue_fields_from_row(row):
    return {
        "name": row["Venue_Location_Name"].strip(),
        "state": row["Map_State"].strip().upper()[:2],
        "city_town": row["Map_City_Town"].strip(),
        "county": row["Map_County"].strip(),
        "latitude": parse_float(row["Map_Latitude"]),
        "longitude": parse_float(row["Map_Longitude"]),
        "is_active": parse_yes_no(row["Venue_Is_Active"]),
        "venue_type": row["Venue_Type"].strip(),
        "size": parse_size(row["Venue_Size"]),
        "genre_notes": row["Venue_Genre_Notes"].strip(),
        "genres": parse_genres(row["Venue_Genre_Search"]),
        "niche_notes": row["Venue_Niche_Notes"].strip(),
        "open_booking": parse_yes_no(row["Venue_Open_Booking"]),
        "booking_type": BOOKING_TYPES_BY_LABEL.get(
            row["Venue_Booking_Type"].strip().lower(), ""
        ),
        "open_mic": parse_yes_no(row["Venue_Open_Mic"]),
        "website": row["Venue_URL"].strip(),
        "booking_url": row["Venue_Booking_URL"].strip(),
        "booking_notes": row["Venue_Booking_Notes"].strip(),
        "age_policy": row["Access_Age"].strip(),
        "accessibility_notes": row["Access_Notes"].strip(),
        "family_friendly": parse_yes_no(row["Access_Family_Friendly"]),
        "lgbtq_friendly": parse_yes_no(row["Access_LGBTQ+"]),
        "diverse": parse_yes_no(row["Access_Diverse"]),
        "safety_flag": row["Access_Safety"].strip(),
        "safety_url": row["Access_Safety_URL"].strip(),
        "safety_notes": row["Access_Safety_Notes"].strip(),
    }


def get_rows_from_google_sheets(sheet_id, tab):
    try:
        result = subprocess.run(
            ["gog", "sheets", "get", sheet_id, f"'{tab}'!A1:ZZ", "--json", "--results-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise CommandError("the gog cli is not installed")
    except subprocess.CalledProcessError as e:
        raise CommandError(f"gog failed: {e.stderr.strip()}")

    values = json.loads(result.stdout)
    header, *rows = values
    # the sheets api drops trailing empty cells, so pad each row out to the header
    return [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in rows]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
        parser.add_argument("--tab", default=DEFAULT_TAB)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would change without saving anything",
        )

    def handle(self, *args, **options):
        rows = get_rows_from_google_sheets(options["sheet_id"], options["tab"])

        if rows and "Venue_ID" not in rows[0]:
            raise CommandError("the sheet has no Venue_ID column")

        nmb_created = 0
        nmb_updated = 0
        seen_sheet_ids = set()

        with transaction.atomic():
            for line_number, row in enumerate(rows, start=2):
                sheet_id = row["Venue_ID"].strip()
                if not sheet_id:
                    if row["Venue_Location_Name"].strip():
                        self.stdout.write(
                            self.style.WARNING(f"row {line_number}: no Venue_ID, skipping")
                        )
                    continue
                if sheet_id in seen_sheet_ids:
                    raise CommandError(
                        f"row {line_number}: Venue_ID {sheet_id} is used more than once"
                    )
                seen_sheet_ids.add(sheet_id)

                fields = venue_fields_from_row(row)
                if row["Venue_Booking_Type"].strip() and not fields["booking_type"]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"row {line_number}: unknown booking type {row['Venue_Booking_Type']!r}"
                        )
                    )

                _, created = Venue.objects.update_or_create(
                    sheet_id=sheet_id, defaults=fields
                )
                if created:
                    nmb_created += 1
                else:
                    nmb_updated += 1

            missing_from_sheet = Venue.objects.exclude(sheet_id__in=seen_sheet_ids)
            for venue in missing_from_sheet:
                self.stdout.write(
                    self.style.WARNING(
                        f"not in sheet (left as is): {venue} [{venue.sheet_id or 'no Venue_ID'}]"
                    )
                )

            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry run] ' if options['dry_run'] else ''}"
                f"created {nmb_created} venues, updated {nmb_updated} venues"
            )
        )
