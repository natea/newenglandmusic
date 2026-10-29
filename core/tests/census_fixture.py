"""
a fake census gazetteer download for tests: small zip files in the real 2026 format ("|"-
separated, with the census's own column names and name suffixes), built here, so no
request leaves the test. the points are the real files' for these places.
"""

import io
import zipfile
from types import SimpleNamespace
from unittest import mock

from core.artist_matching import normalize
from core.models import CensusPlace

ZCTAS = [("02144", 42.400077, -71.123088), ("02139", 42.364688, -71.104155), ("05656", 44.648124, -72.68884)]
COUSUBS = [
    ("MA", "Somerville city", 42.390445, -71.101033),
    ("ME", "Somerville town", 44.289274, -69.485747),
    ("MA", "Cambridge city", 42.375100, -71.105600),
    ("CT", "Hamden town", 41.397329, -72.922226),
    ("NY", "Hamden town", 42.190000, -74.980000),
    ("MA", "Springfield city", 42.115500, -72.539500),
    ("VT", "Springfield town", 43.298400, -72.482300),
    ("NJ", "Springfield township", 40.700000, -74.320000),
    ("VT", "Johnson town", 44.648124, -72.68884),
]
PLACES = [
    ("MA", "Somerville city", 42.390445, -71.101033),
    ("VT", "Johnson village", 44.636000, -72.680000),
    ("NY", "Brooklyn Heights CDP", 40.695800, -73.993500),
]


def gazetteer_zip(name, header, rows):
    text = "|".join(header) + "\n" + "\n".join("|".join(str(cell) for cell in row) for row in rows) + "\n"
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(f"2026_Gaz_{name}.txt", text)
    return out.getvalue()


def files():
    town_header = ["USPS", "GEOID", "NAME", "ALAND", "INTPTLAT", "INTPTLONG"]
    return {
        "zcta_national": gazetteer_zip(
            "zcta_national", ["GEOID", "ALAND", "INTPTLAT", "INTPTLONG"], [(z, 1, lat, lon) for z, lat, lon in ZCTAS]
        ),
        "cousubs_national": gazetteer_zip(
            "cousubs_national", town_header, [(s, i, n, 1, lat, lon) for i, (s, n, lat, lon) in enumerate(COUSUBS)]
        ),
        "place_national": gazetteer_zip(
            "place_national", town_header, [(s, i, n, 1, lat, lon) for i, (s, n, lat, lon) in enumerate(PLACES)]
        ),
    }


class FakeCensus:
    """answers the gazetteer downloads; `failing` names a file to answer with 503"""

    def __init__(self, failing=None, year=2026):
        self.files = files()
        self.failing = failing
        self.year = year
        self.requests = []

    def get(self, url, headers=None, timeout=None):
        self.requests.append(url)
        name = url.rsplit(f"{self.year}_Gaz_", 1)[-1].removesuffix(".zip")
        if name == self.failing or name not in self.files or f"/{self.year}_Gazetteer/" not in url:
            return SimpleNamespace(status_code=503, content=b"")
        return SimpleNamespace(status_code=200, content=self.files[name])

    def patch(self):
        return mock.patch("core.management.commands.load_census_gazetteer.session", lambda: self)


def census_places():
    """the fixture's places as rows, without going through the command"""
    rows = [CensusPlace(kind="zip", name=z, state="", search_key=z, latitude=lat, longitude=lon) for z, lat, lon in ZCTAS]
    seen = set()
    for state, name, lat, lon in COUSUBS + PLACES:
        town = name.rsplit(" ", 1)[0]
        if (town, state) in seen:
            continue
        seen.add((town, state))
        rows.append(CensusPlace(kind="town", name=town, state=state, search_key=normalize(town), latitude=lat, longitude=lon))
    CensusPlace.objects.bulk_create(rows)
