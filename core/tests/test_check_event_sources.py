import csv
import os
import tempfile
from io import StringIO
from unittest import mock

import requests
from bs4 import BeautifulSoup
from core.management.commands import check_event_sources as check
from core.event_sources import CSV_COLUMNS
from core.models import Venue, VenueEventSource
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

LONG_TEXT = "<p>" + "Live music every night of the week. " * 20 + "</p>"
ICAL = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:a\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nSUMMARY:b\r\nEND:VEVENT\r\nEND:VCALENDAR"


def soup(html):
    return BeautifulSoup(html, "html.parser")


def response(url, status=200, text=""):
    r = requests.Response()
    r.status_code = status
    r.url = url
    r._content = text.encode()
    r.encoding = "utf-8"
    return r


class FakeSession:
    """answers get() from a dict of url -> response or exception; anything else is a 404"""

    def __init__(self, pages):
        self.pages = pages
        self.headers = {}
        self.requested = []

    def get(self, url, timeout=None):
        self.requested.append(url)
        page = self.pages.get(url)
        if isinstance(page, Exception):
            raise page
        if page is None:
            return response(url, 404)
        if isinstance(page, requests.Response):
            return page
        return response(url, 200, page)


def venue(website="https://venue.example/", **kwargs):
    return {
        "sheet_id": "V0001",
        "name": "The Venue",
        "state": "VT",
        "city_town": "Burlington",
        "website": website,
        "booking_url": "",
        **kwargs,
    }


class HelpersTestCase(SimpleTestCase):
    def test_nav_calendar_link_beats_single_event_links(self):
        page = soup(
            """
            <nav><a href="/calendar">Calendar</a><a href="/about">About</a></nav>
            <a href="/events/jazz-night-10-24-2026">Jazz night</a>
            <a href="https://other.example/events">Events elsewhere</a>
            """
        )
        self.assertEqual(
            check.find_events_page_url(page, "https://venue.example/"),
            "https://venue.example/calendar",
        )

    def test_private_events_and_rentals_are_not_listings(self):
        page = soup(
            '<a href="/private-events">Private Events</a>'
            '<a href="/events-space">Rent our space for events</a>'
        )
        self.assertIsNone(check.find_events_page_url(page, "https://venue.example/"))

    def test_only_single_event_links_means_no_listing(self):
        page = soup('<a href="/events/12345">Show</a><a href="/event/2026-11-05">Show</a>')
        self.assertIsNone(check.find_events_page_url(page, "https://venue.example/"))

    def test_file_links_and_self_links_are_skipped(self):
        page = soup('<a href="/calendar.pdf">Calendar</a><a href="/#shows">Shows</a>')
        self.assertIsNone(check.find_events_page_url(page, "https://venue.example/"))

    def test_looks_like_single_event_page(self):
        for path in (
            "/products/events/jazz-jam-saturday-10-24-2026-4-00-pm-53552652",
            "/events/12345",
            "/2026/11/05/show",
            "/events/an-evening-with-a-very-long-band-name-and-friends-tour",
        ):
            self.assertTrue(check.looks_like_single_event_page(path), path)
        for path in ("/events", "/calendar/", "/shows/upcoming"):
            self.assertFalse(check.looks_like_single_event_page(path), path)

    def test_find_ical_urls(self):
        page = soup(
            """
            <a href="webcal://venue.example/cal.ics">Subscribe</a>
            <link type="text/calendar" href="/feed">
            <a href="/events/?ical=1">iCal</a>
            <a href="/events/?ical=1">iCal again</a>
            <a href="/about">About</a>
            """
        )
        self.assertEqual(
            check.find_ical_urls(page, "https://venue.example/"),
            [
                "https://venue.example/cal.ics",
                "https://venue.example/feed",
                "https://venue.example/events/?ical=1",
            ],
        )

    def test_count_json_ld_events(self):
        page = soup(
            """
            <script type="application/ld+json">
              {"@graph": [{"@type": "MusicEvent"}, {"@type": "Organization"}]}
            </script>
            <script type="application/ld+json">{not json</script>
            <script type="application/ld+json">[{"@type": ["Event", "Thing"]}]</script>
            """
        )
        self.assertEqual(check.count_json_ld_events(page), 2)

    def test_find_platforms(self):
        html = '<a href="https://www.Eventbrite.com/e/1">x</a><iframe src="https://dice.fm/x">'
        self.assertEqual(check.find_platforms(html), ["dice", "eventbrite"])
        self.assertEqual(check.find_platforms("<p>no tickets</p>"), [])

    def test_is_social_and_normalize_url(self):
        self.assertTrue(check.is_social("https://www.facebook.com/thevenue"))
        self.assertTrue(check.is_social("https://linktr.ee/thevenue"))
        self.assertFalse(check.is_social("https://venue.example"))
        self.assertEqual(check.normalize_url(" venue.example/shows "), "https://venue.example/shows")
        self.assertEqual(check.normalize_url("HTTP://venue.example"), "HTTP://venue.example")
        self.assertEqual(check.normalize_url(""), "")


class CheckVenueTestCase(SimpleTestCase):
    def check(self, pages, **venue_kwargs):
        session = FakeSession(pages)
        with mock.patch.object(check.requests, "Session", return_value=session):
            result = check.check_venue(venue(**venue_kwargs))
        return result, session

    def test_ical_is_preferred(self):
        result, session = self.check(
            {
                "https://venue.example/": '<a href="/cal.ics">iCal</a>'
                '<script type="application/ld+json">{"@type": "Event"}</script>'
                + LONG_TEXT,
                "https://venue.example/cal.ics": ICAL,
            }
        )
        self.assertEqual(result["best_source"], "ical")
        self.assertEqual(result["ical_url"], "https://venue.example/cal.ics")
        self.assertEqual(result["ical_events"], 2)
        self.assertEqual(result["json_ld_events"], 1)
        self.assertEqual(session.headers["User-Agent"], check.USER_AGENT)

    def test_linked_feed_that_isnt_a_calendar_is_not_used(self):
        result, _ = self.check(
            {
                "https://venue.example/": '<a href="/cal.ics">iCal</a>' + LONG_TEXT,
                "https://venue.example/cal.ics": "<html>not a calendar</html>",
            }
        )
        self.assertEqual(result["best_source"], "ai-extraction")
        self.assertEqual(result["ical_url"], "")

    def test_wordpress_events_calendar_feed_is_tried(self):
        result, session = self.check(
            {
                "https://venue.example/": '<div class="tribe-events">' + LONG_TEXT + "</div>",
                "https://venue.example/events/?ical=1": ICAL,
            }
        )
        self.assertIn("https://venue.example/events/?ical=1", session.requested)
        self.assertEqual(result["best_source"], "ical")

    def test_json_ld_on_the_events_page(self):
        result, _ = self.check(
            {
                "https://venue.example/": '<nav><a href="/calendar">Calendar</a></nav>' + LONG_TEXT,
                "https://venue.example/calendar": '<script type="application/ld+json">'
                '[{"@type": "MusicEvent"}, {"@type": "MusicEvent"}]</script>',
            }
        )
        self.assertEqual(result["best_source"], "json-ld")
        self.assertEqual(result["events_page"], "https://venue.example/calendar")
        self.assertEqual(result["json_ld_events"], 2)

    def test_ticketing_links(self):
        result, _ = self.check(
            {"https://venue.example/": '<a href="https://www.ticketweb.com/e/1">Tix</a>' + LONG_TEXT}
        )
        self.assertEqual(result["best_source"], "ticketing")
        self.assertEqual(result["platforms"], "ticketweb")

    def test_plain_page_is_ai_extraction(self):
        result, _ = self.check({"https://venue.example/": LONG_TEXT})
        self.assertEqual(result["best_source"], "ai-extraction")
        self.assertEqual(result["js_heavy"], "")

    def test_script_rendered_page_is_flagged(self):
        result, _ = self.check(
            {"https://venue.example/": "<div id=app></div><script>render()</script>"}
        )
        self.assertEqual(result["js_heavy"], "yes")

    def test_no_website(self):
        result, session = self.check({}, website="")
        self.assertEqual(result["best_source"], "no-website")
        self.assertEqual(session.requested, [])

    def test_booking_url_is_used_without_a_website(self):
        result, _ = self.check(
            {"https://book.example/": LONG_TEXT}, website="", booking_url="https://book.example/"
        )
        self.assertEqual(result["best_source"], "ai-extraction")

    def test_social_only(self):
        result, session = self.check({}, website="https://www.facebook.com/thevenue")
        self.assertEqual(result["best_source"], "social-only")
        self.assertEqual(session.requested, [])

    def test_robots_blocked(self):
        result, session = self.check(
            {
                "https://venue.example/robots.txt": "User-agent: *\nDisallow: /",
                "https://venue.example/": LONG_TEXT,
            }
        )
        self.assertEqual(result["best_source"], "robots-blocked")
        self.assertNotIn("https://venue.example/", session.requested)

    def test_dead_domain(self):
        error = requests.ConnectionError("NameResolutionError: venue.example")
        result, _ = self.check({"https://venue.example/": error})
        self.assertEqual(result["best_source"], "dead-domain")

    def test_bot_blocked(self):
        for status in (403, 406, 429):
            result, _ = self.check(
                {"https://venue.example/": response("https://venue.example/", status)}
            )
            self.assertEqual(result["best_source"], "bot-blocked", status)
            self.assertIn(str(status), result["error"])

    def test_unreachable(self):
        result, _ = self.check({"https://venue.example/": requests.Timeout("timed out")})
        self.assertEqual(result["best_source"], "unreachable")

    def test_404_falls_back_to_homepage_and_records_it(self):
        result, _ = self.check(
            {"https://venue.example/": LONG_TEXT},
            website="https://venue.example/old-events",
        )
        self.assertEqual(result["best_source"], "ai-extraction")
        self.assertEqual(result["url"], "https://venue.example/")

    def test_records_the_url_after_redirects(self):
        result, _ = self.check(
            {
                "https://venue.example/": response(
                    "https://www.venue.example/home", 200, LONG_TEXT
                )
            }
        )
        self.assertEqual(result["url"], "https://www.venue.example/home")

    def test_unexpected_error_is_check_failed(self):
        with mock.patch.object(check, "check_venue_unsafe", side_effect=RuntimeError("boom")):
            result = check.check_venue(venue())
        self.assertEqual(result["best_source"], "check-failed")
        self.assertEqual(result["error"], "RuntimeError: boom")


class CheckCommandTestCase(TestCase):
    def setUp(self):
        Venue.objects.create(sheet_id="V0001", name="NH open", state="NH", is_active=True)
        Venue.objects.create(sheet_id="V0002", name="NH unknown", state="NH", is_active=None)
        Venue.objects.create(sheet_id="V0003", name="NH closed", state="NH", is_active=False)
        Venue.objects.create(sheet_id="V0004", name="MA open", state="MA", is_active=True)
        self.results = {}

    def run_check(self, *args):
        """runs the check with canned results; returns the sheet ids it checked"""
        checked = []

        def fake_check(venue):
            checked.append(venue["sheet_id"])
            return {
                "sheet_id": venue["sheet_id"],
                "name": venue["name"],
                "best_source": "ical",
                **self.results.get(venue["sheet_id"], {}),
            }

        with mock.patch.object(check, "check_venue", side_effect=fake_check):
            call_command("check_event_sources", *args, stdout=StringIO())
        return sorted(checked)

    def saved(self, sheet_id):
        return VenueEventSource.objects.get(venue__sheet_id=sheet_id)

    def test_state_filter_skips_inactive_venues(self):
        self.assertEqual(self.run_check("--state", "nh"), ["V0001", "V0002"])

    def test_include_inactive(self):
        self.assertEqual(
            self.run_check("--state", "NH", "--include-inactive"), ["V0001", "V0002", "V0003"]
        )

    def test_sheet_ids(self):
        self.assertEqual(self.run_check("--sheet-ids", "V0001,V0004"), ["V0001", "V0004"])

    def test_limit(self):
        self.assertEqual(len(self.run_check("--limit", "2")), 2)

    def test_first_check_of_a_venue(self):
        self.results["V0001"] = {
            "ical_url": "https://v0001.example/cal.ics",
            "ical_events": 12,
        }
        before = timezone.now()
        self.run_check("--state", "NH")
        source = self.saved("V0001")
        self.assertEqual(source.best_source, "ical")
        self.assertEqual(source.ical_url, "https://v0001.example/cal.ics")
        self.assertEqual(source.ical_events, 12)
        self.assertGreaterEqual(source.checked_at, before)

    def test_recheck_replaces_the_result(self):
        self.results["V0001"] = {"ical_url": "https://v0001.example/cal.ics", "ical_events": 12}
        self.run_check("--state", "NH")
        self.results["V0001"] = {"best_source": "ticketing", "platforms": "dice;eventbrite"}
        self.run_check("--state", "NH")
        self.assertEqual(VenueEventSource.objects.filter(venue__sheet_id="V0001").count(), 1)
        source = self.saved("V0001")
        self.assertEqual(source.best_source, "ticketing")
        self.assertEqual(source.platforms, ["dice", "eventbrite"])
        self.assertEqual(source.ical_url, "")

    def test_partial_run_keeps_other_results(self):
        self.run_check()
        ma_checked_at = self.saved("V0004").checked_at
        self.results["V0001"] = {"best_source": "ai-extraction"}
        # the state filter: only active NH venues are checked, and only their results change
        self.assertEqual(self.run_check("--state", "NH"), ["V0001", "V0002"])
        self.assertEqual(self.saved("V0001").best_source, "ai-extraction")
        self.assertEqual(self.saved("V0004").best_source, "ical")
        self.assertEqual(self.saved("V0004").checked_at, ma_checked_at)
        self.assertFalse(VenueEventSource.objects.filter(venue__sheet_id="V0003").exists())

    def test_report_lists_each_venue(self):
        self.results["V0001"] = {
            "url": "https://v0001.example/",
            "events_page": "https://v0001.example/calendar/",
            "ical_url": "https://v0001.example/events/?ical=1",
            "ical_events": 23,
            "platforms": "dice;eventbrite",
            "js_heavy": "yes",
        }
        self.results["V0002"] = {"best_source": "bot-blocked", "error": "HTTP 403"}
        out = StringIO()
        with mock.patch.object(check, "check_venue", side_effect=lambda venue: {
            "sheet_id": venue["sheet_id"],
            "name": venue["name"],
            "best_source": "ical",
            **self.results.get(venue["sheet_id"], {}),
        }):
            call_command("check_event_sources", "--state", "NH", stdout=out, no_color=True)
        output = out.getvalue()
        self.assertIn("V0001 NH open (NH): ical", output)
        self.assertIn("  events page: https://v0001.example/calendar/", output)
        self.assertIn("  ical feed: https://v0001.example/events/?ical=1 (23 events)", output)
        self.assertIn("  ticketing: dice, eventbrite · little text without javascript", output)
        self.assertIn("V0002 NH unknown (NH): bot-blocked", output)
        self.assertIn("  error: HTTP 403", output)

    def test_csv_export(self):
        self.results["V0001"] = {"platforms": "dice", "js_heavy": "yes"}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sources.csv")
            self.run_check("--state", "NH", "--csv", path)
            with open(path) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        self.assertEqual(reader.fieldnames, CSV_COLUMNS)
        self.assertEqual([row["sheet_id"] for row in rows], ["V0001", "V0002"])
        self.assertEqual(rows[0]["platforms"], "dice")
        self.assertEqual(rows[0]["js_heavy"], "yes")
        self.assertEqual(VenueEventSource.objects.count(), 2)

    def test_no_file_without_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                self.run_check()
            finally:
                os.chdir(cwd)
            self.assertEqual(os.listdir(tmp), [])

    def test_user_agent_identifies_the_crawler(self):
        self.assertEqual(check.USER_AGENT, "Mozilla/5.0 (compatible; venue-db-event-check/1.0)")
