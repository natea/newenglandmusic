from pathlib import Path
from unittest import mock

from core.management.commands import sync_venues_from_gsheets as sync

# a trimmed copy of the sheet's geo-filters_json tab, as `gog --json --results-only` prints it
FIXTURE = Path(__file__).parent / "fixtures" / "geo_filters.json"


def geo_fixture_rows():
    """the fixture's rows, read through the same parsing as a real gog call"""
    stdout = FIXTURE.read_text()
    with mock.patch.object(sync.subprocess, "run", return_value=mock.Mock(stdout=stdout)):
        return sync.get_rows_from_google_sheets("sheet-id", sync.DEFAULT_GEO_TAB)


def load_geo_fixture():
    """the site's own areas (core/geo_areas.py), as every migrate loads them"""
    from core.geo_area_sync import sync_geo_areas

    sync_geo_areas()
