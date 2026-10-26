import json
import subprocess
from collections import Counter

from core import google_sheets
from core.geo_filters import area_q
from core.models import GeoArea, Venue
from core.job_runs import RecordedCommand
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

"""
syncs venues from the "Northeastern US Music Venues" google sheet into the db,
along with the regions, states and metro areas the site filters events by.

run as:

python manage.py sync_venues_from_gsheets [--dry-run]

on a server, the sheet is read with a google cloud service account whose json key is in
GOOGLE_SERVICE_ACCOUNT_JSON (see core/google_sheets.py and PRODUCTION.md). without
it, it's read with the gog cli, which must be installed and authorized with the sheets
service.

every row must have a Venue_ID (e.g. V0042) -- venues are matched on it, so it
must never change for a given row. rows are created or updated; venues that are
no longer in the sheet are reported but never deleted.

areas come from the geo-filters_json tab, one matching rule per row; rows that
share an ID make up one area. unlike venues, areas are configuration: after a
sync the stored areas are exactly the ones in the tab.
"""

DEFAULT_SHEET_ID = "1QBzKHOUWOR0Fw0ODrwEep5eGfZg4SmTUq4PsaCbbnGQ"
DEFAULT_TAB = "V3 - Flattened"
DEFAULT_GEO_TAB = "geo-filters_json"

# the geo-filters_json MATCH_TYPE values and the GeoArea list each one fills
RULE_FIELDS = {"state": "states", "county": "counties", "city": "cities"}

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


def get_values_with_gog(sheet_id, a1_range, tab):
    try:
        result = subprocess.run(
            ["gog", "sheets", "get", sheet_id, a1_range, "--json", "--results-only"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        raise CommandError("the gog cli is not installed")
    except subprocess.CalledProcessError as e:
        raise CommandError(f"gog failed reading tab {tab!r}: {e.stderr.strip()}")
    return json.loads(result.stdout)


def get_rows_from_google_sheets(sheet_id, tab):
    """
    the tab's rows as dicts keyed by its header row. read with a service account when
    GOOGLE_SERVICE_ACCOUNT_JSON is set (on a server), and with the gog cli otherwise
    """
    a1_range = f"'{tab}'!A1:ZZ"
    if google_sheets.is_configured():
        values = google_sheets.read_values(sheet_id, a1_range, tab)
    else:
        values = get_values_with_gog(sheet_id, a1_range, tab)
    header, *rows = values
    # the sheets api drops trailing empty cells, so pad each row out to the header
    return [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in rows]


def split_values(value):
    # "Brookline, Cambridge, Somerville" -> ["brookline", "cambridge", "somerville"]
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def geo_areas_from_rows(rows):
    """
    groups geo-filters_json rows into GeoArea field dicts, in the order each
    area first appears. returns (areas, warnings).
    """
    areas = {}
    warnings = []
    for row in rows:
        kind = row["FILTER_TYPE"].strip()
        sheet_id = row["ID"].strip()
        match_type = row["MATCH_TYPE"].strip()
        if not kind and not sheet_id:
            continue
        # the "ALL" row stands for no filter at all
        if match_type == "any":
            continue
        if kind not in GeoArea.Kind.values:
            warnings.append(f"{sheet_id}: unknown filter type {kind!r}, skipping")
            continue
        if match_type not in RULE_FIELDS:
            warnings.append(f"{sheet_id}: unknown match type {match_type!r}, skipping")
            continue

        if sheet_id not in areas:
            label = row["LABEL"].strip()
            home_state = row["STATE"].strip().upper()
            areas[sheet_id] = {
                "kind": kind,
                "label": label,
                # regions list several states here; only a single state is a home
                "home_state": home_state if len(home_state) == 2 else "",
                "slug": slugify(label),
                "sort_order": len(areas),
                "states": [],
                "counties": [],
                "cities": [],
            }
        areas[sheet_id][RULE_FIELDS[match_type]] += split_values(row["VALUES"])

    seen_slugs = set()
    for sheet_id, fields in areas.items():
        key = (fields["kind"], fields["slug"])
        if key in seen_slugs:
            raise CommandError(
                f"{sheet_id}: another {fields['kind']} already has the url slug {fields['slug']!r}"
            )
        seen_slugs.add(key)
    return areas, warnings


def save_geo_areas(areas):
    """replaces the stored areas with areas. returns (added, updated, removed)."""
    nmb_added = nmb_updated = 0
    existing = {area.sheet_id: area for area in GeoArea.objects.all()}
    for sheet_id, fields in areas.items():
        area = existing.get(sheet_id)
        if area is None:
            GeoArea.objects.create(sheet_id=sheet_id, **fields)
            nmb_added += 1
        else:
            changed = {name for name, value in fields.items() if getattr(area, name) != value}
            if changed:
                GeoArea.objects.filter(pk=area.pk).update(**fields)
            # adding or removing a row shifts the sort order of every area after it,
            # which isn't worth reporting as an update
            if changed - {"sort_order"}:
                nmb_updated += 1
    nmb_removed, _ = GeoArea.objects.exclude(sheet_id__in=areas).delete()
    return nmb_added, nmb_updated, nmb_removed


def venues_in_no_metro_by_state():
    in_a_metro = Q(pk__in=[])
    for metro in GeoArea.objects.filter(kind=GeoArea.Kind.METRO):
        in_a_metro |= area_q(metro)
    return Counter(Venue.objects.exclude(in_a_metro).values_list("state", flat=True))


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
        parser.add_argument("--tab", default=DEFAULT_TAB)
        parser.add_argument("--geo-tab", default=DEFAULT_GEO_TAB)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would change without saving anything",
        )

    def handle(self, *args, **options):
        # read both tabs before changing anything, so a missing tab changes nothing
        rows = get_rows_from_google_sheets(options["sheet_id"], options["tab"])
        geo_rows = get_rows_from_google_sheets(options["sheet_id"], options["geo_tab"])

        if rows and "Venue_ID" not in rows[0]:
            raise CommandError("the sheet has no Venue_ID column")

        geo_areas, geo_warnings = geo_areas_from_rows(geo_rows)
        for warning in geo_warnings:
            self.stdout.write(self.style.WARNING(warning))

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

            nmb_added, nmb_area_updated, nmb_removed = save_geo_areas(geo_areas)
            no_metro = venues_in_no_metro_by_state()

            if options["dry_run"]:
                transaction.set_rollback(True)

        dry_run = "[dry run] " if options["dry_run"] else ""
        if no_metro:
            counts = ", ".join(f"{state or '?'} {count}" for state, count in sorted(no_metro.items()))
            self.stdout.write(f"{dry_run}venues in no metro area: {counts}")
        self.job_summary = [
            ("venues created", nmb_created),
            ("venues updated", nmb_updated),
            ("areas added", nmb_added),
            ("areas updated", nmb_area_updated),
            ("areas removed", nmb_removed),
        ]
        self.stdout.write(
            self.style.SUCCESS(
                f"{dry_run}created {nmb_created} venues, updated {nmb_updated} venues; "
                f"added {nmb_added} areas, updated {nmb_area_updated}, removed {nmb_removed}"
            )
        )
