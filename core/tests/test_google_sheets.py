import json
import os
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core import google_sheets
from core.management.commands import sync_venues_from_gsheets as sync
from core.models import GeoArea, Venue
from core.tests.test_sync_venues_from_gsheets import COLUMNS, row
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from google.auth.exceptions import RefreshError

GEO_VALUES = json.loads((Path(__file__).parent / "fixtures" / "geo_filters.json").read_text())

# a fake key with recognisable secrets, which must never appear in any output
PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nSECRET-KEY-MATERIAL-12345\n-----END PRIVATE KEY-----\n"
TOKEN = "ya29.SECRET-ACCESS-TOKEN"
KEY = {
    "type": "service_account",
    "client_email": "venue-sync@newenglandmusic.iam.gserviceaccount.com",
    "private_key": PRIVATE_KEY,
    "token_uri": "https://oauth2.googleapis.com/token",
}
SECRETS = (PRIVATE_KEY, "SECRET-KEY-MATERIAL", TOKEN, json.dumps(KEY))



def venue_values(*rows):
    """a venue tab's values, as the sheets api returns them"""
    return [COLUMNS, *[[r[c] for c in COLUMNS] for r in rows]]


def response(status, body):
    return SimpleNamespace(status_code=status, json=lambda: body)


class ServiceAccountTestCase(SimpleTestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {google_sheets.ENV_VAR: json.dumps(KEY)})
        env.start()
        self.addCleanup(env.stop)
        credentials = mock.patch.object(
            google_sheets.service_account.Credentials, "from_service_account_info"
        )
        self.credentials = credentials.start()
        self.addCleanup(credentials.stop)

    def read(self, *responses, tab="geo-filters_json"):
        with mock.patch.object(
            google_sheets.AuthorizedSession, "get", side_effect=list(responses)
        ) as get, mock.patch.object(sync.subprocess, "run") as run:
            rows = sync.get_rows_from_google_sheets("sheet-id", tab)
        return rows, get, run

    def test_service_account_configured(self):
        rows, get, run = self.read(response(200, {"values": GEO_VALUES}))
        run.assert_not_called()
        self.assertEqual(self.credentials.call_args.kwargs["scopes"], google_sheets.SCOPES)
        self.assertEqual(google_sheets.SCOPES, ["https://www.googleapis.com/auth/spreadsheets.readonly"])
        url = get.call_args.args[0]
        self.assertIn("/spreadsheets/sheet-id/values/", url)
        # the range is url-encoded, so tab names with spaces work
        self.assertIn("%27geo-filters_json%27%21A1%3AZZ", url)
        self.assertEqual(get.call_args.kwargs["params"], {"valueRenderOption": "FORMATTED_VALUE"})
        self.assertEqual(rows[0]["FILTER_TYPE"], "region")

    def test_same_rows_either_way(self):
        api_rows, _, _ = self.read(response(200, {"values": GEO_VALUES}))
        with mock.patch.dict(os.environ, {google_sheets.ENV_VAR: ""}), mock.patch.object(
            sync.subprocess, "run", return_value=mock.Mock(stdout=json.dumps(GEO_VALUES))
        ):
            gog_rows = sync.get_rows_from_google_sheets("sheet-id", "geo-filters_json")
        self.assertEqual(api_rows, gog_rows)

    def test_short_rows_are_padded(self):
        rows, _, _ = self.read(response(200, {"values": [["a", "b", "c"], ["1"]]}))
        self.assertEqual(rows, [{"a": "1", "b": "", "c": ""}])

    def test_invalid_key(self):
        for bad in ("not json", json.dumps({"type": "authorized_user"}), "[]"):
            with mock.patch.dict(os.environ, {google_sheets.ENV_VAR: bad}):
                with self.assertRaises(CommandError) as raised:
                    self.read()
                self.assertEqual(
                    str(raised.exception),
                    "GOOGLE_SERVICE_ACCOUNT_JSON isn't a valid service-account key",
                )

    def test_sheet_not_shared(self):
        for status in (403, 404):
            with self.assertRaises(CommandError) as raised:
                self.read(response(status, {"error": {"message": "The caller does not have permission"}}))
            self.assertEqual(
                str(raised.exception),
                "can't read tab 'geo-filters_json': share the sheet with "
                "venue-sync@newenglandmusic.iam.gserviceaccount.com as a Viewer",
            )

    def test_sheets_api_disabled(self):
        disabled = {"error": {
            "status": "PERMISSION_DENIED",
            "message": "Google Sheets API has not been used in project 123 before or it is disabled.",
            "details": [{"reason": "SERVICE_DISABLED"}],
        }}
        with self.assertRaisesMessage(CommandError, "the google sheets api isn't enabled"):
            self.read(response(403, disabled))

    def test_missing_tab(self):
        with self.assertRaisesMessage(CommandError, "tab 'geo-filters_json' doesn't exist"):
            self.read(response(400, {"error": {"message": "Unable to parse range: 'geo-filters_json'!A1:ZZ"}}))

    def test_other_errors(self):
        with self.assertRaisesMessage(CommandError, "can't read tab 'geo-filters_json': HTTP 500 Internal error"):
            self.read(response(500, {"error": {"message": "Internal error"}}))

    def test_nothing_secret_in_errors(self):
        failures = [
            response(403, {"error": {"message": "denied"}}),
            response(400, {"error": {"message": "Unable to parse range"}}),
            response(500, {"error": {"message": "boom"}}),
            RefreshError(f"invalid_grant: {TOKEN}", {"access_token": TOKEN}),
        ]
        for failure in failures:
            with self.assertRaises(CommandError) as raised:
                self.read(failure)
            message = str(raised.exception)
            self.assertIsNone(raised.exception.__cause__)
            for secret in SECRETS:
                self.assertNotIn(secret, message)


class SyncWithServiceAccountTestCase(TestCase):
    """a full sync run, read with the service account"""

    def setUp(self):
        env = mock.patch.dict(os.environ, {google_sheets.ENV_VAR: json.dumps(KEY)})
        env.start()
        self.addCleanup(env.stop)
        credentials = mock.patch.object(
            google_sheets.service_account.Credentials, "from_service_account_info"
        )
        credentials.start()
        self.addCleanup(credentials.stop)
        Venue.objects.create(sheet_id="V0001", name="Before", state="VT")

    def sync(self, venue_response, geo_response):
        def get(url, params=None, timeout=None):
            return geo_response if "geo-filters_json" in url else venue_response

        out, err = StringIO(), StringIO()
        with mock.patch.object(google_sheets.AuthorizedSession, "get", side_effect=get):
            call_command("sync_venues_from_gsheets", stdout=out, stderr=err)
        return out.getvalue() + err.getvalue()

    def test_missing_geo_tab_changes_nothing(self):
        venues = response(200, {"values": venue_values(row("V0001", "After"))})
        missing = response(400, {"error": {"message": "Unable to parse range: geo-filters_json"}})
        with self.assertRaisesMessage(CommandError, "tab 'geo-filters_json' doesn't exist"):
            self.sync(venues, missing)
        self.assertEqual(Venue.objects.get(sheet_id="V0001").name, "Before")
        self.assertFalse(GeoArea.objects.exists())

    def test_sync_reads_both_tabs(self):
        venues = response(200, {"values": venue_values(row("V0001", "After"))})
        output = self.sync(venues, response(200, {"values": GEO_VALUES}))
        self.assertEqual(Venue.objects.get(sheet_id="V0001").name, "After")
        self.assertTrue(GeoArea.objects.exists())
        for secret in SECRETS:
            self.assertNotIn(secret, output)
