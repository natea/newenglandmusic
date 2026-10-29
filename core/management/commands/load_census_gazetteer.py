import csv
import io
import re
import zipfile

import requests
from core.artist_matching import normalize
from core.models import CensusPlace
from core.user_agent import USER_AGENT
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

"""
loads the census bureau's gazetteer files into CensusPlace, so the location form can turn a
zip code or town into a point (core/location.py) without asking any service per search.

run as:

python manage.py load_census_gazetteer [--year 2026]

the files are public domain, updated once a year: zip code tabulation areas, county
subdivisions (new england's towns) and places (cities, villages and boroughs elsewhere).
the table is replaced in one transaction, and left as it was when a download fails. run it
once at setup and again each year (see PRODUCTION.md).
"""

DEFAULT_YEAR = 2026
URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{year}_Gazetteer/{year}_Gaz_{name}.zip"
TIMEOUT_SECONDS = 120
ZIP_FILE = "zcta_national"
# county subdivisions first: in new england they're the towns people mean
TOWN_FILES = ("cousubs_national", "place_national")
# the census's words for what kind of place a name is ("Somerville city", "Hamden town")
SUFFIXES = (
    "charter township", "unorganized territory", "city and borough", "consolidated government",
    "metropolitan government", "unified government", "urban county", "city", "town", "cdp",
    "village", "borough", "township", "plantation", "gore", "grant", "location", "purchase",
    "municipality", "comunidad", "zona urbana",
)
SUFFIX_RE = re.compile(rf"\s+(?:{'|'.join(re.escape(s) for s in SUFFIXES)})$", re.IGNORECASE)


def session():
    return requests.Session()


def strip_suffix(name):
    """"Somerville city" -> "Somerville"; a name that's only a suffix stays as it is"""
    stripped = SUFFIX_RE.sub("", name.strip())
    return stripped or name.strip()


def read_rows(content):
    """the rows of a gazetteer zip file, as dicts keyed by its stripped column names"""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".txt"))
        raw = archive.read(name)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    lines = text.splitlines()
    # the files were tab-separated until 2024, and use "|" since 2025
    delimiter = "|" if "|" in lines[0] else "\t"
    reader = csv.reader(lines, delimiter=delimiter)
    head = [h.strip() for h in next(reader)]
    return [dict(zip(head, [cell.strip() for cell in row])) for row in reader if row]


class Command(BaseCommand):
    help = "load the census gazetteer's zip code areas and towns for the location form"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="the gazetteer year to load")

    def handle(self, *args, **options):
        year = options["year"]
        http = session()
        files = {name: self.download(http, year, name) for name in (ZIP_FILE, *TOWN_FILES)}

        places = []
        for row in read_rows(files[ZIP_FILE]):
            code = row.get("GEOID", "")
            if re.fullmatch(r"\d{5}", code):
                places.append(self.place(CensusPlace.Kind.ZIP, code, "", row))
        seen = set()
        for name in TOWN_FILES:
            for row in read_rows(files[name]):
                town, state = strip_suffix(row.get("NAME", "")), row.get("USPS", "").upper()
                key = (normalize(town), state)
                if not town or not state or key in seen or town.lower().startswith("county subdivisions not defined"):
                    continue
                seen.add(key)
                places.append(self.place(CensusPlace.Kind.TOWN, town, state, row))

        with transaction.atomic():
            CensusPlace.objects.all().delete()
            CensusPlace.objects.bulk_create(places, batch_size=2000)
        zips = sum(place.kind == CensusPlace.Kind.ZIP for place in places)
        self.stdout.write(f"loaded the {year} gazetteer: {zips} zip code areas and {len(places) - zips} towns")

    def download(self, http, year, name):
        url = URL.format(year=year, name=name)
        try:
            response = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as e:
            raise CommandError(f"couldn't download {url}: {type(e).__name__}; the table is unchanged")
        if response.status_code != 200:
            raise CommandError(f"couldn't download {url}: HTTP {response.status_code}; the table is unchanged")
        return response.content

    def place(self, kind, name, state, row):
        return CensusPlace(
            kind=kind,
            name=name,
            state=state,
            search_key=normalize(name),
            latitude=float(row["INTPTLAT"]),
            longitude=float(row["INTPTLONG"]),
        )
