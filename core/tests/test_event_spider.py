import asyncio
import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.event_fetching import spider as spider_module
from core.event_fetching.spider import (
    SCRAPY_SETTINGS,
    VenueEventsSpider,
    is_ticketing_event_url,
    page_text_for_ai,
)
from core.management.commands.check_event_sources import USER_AGENT
from django.test import SimpleTestCase
from django.utils import timezone
from scrapy.http import HtmlResponse, TextResponse

ICAL = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:test\r\n"
    "BEGIN:VEVENT\r\nUID:a\r\nSUMMARY:Show\r\nDTSTART:20261105T200000\r\nEND:VEVENT\r\n"
    "END:VCALENDAR"
)
JSON_LD_PAGE = (
    '<script type="application/ld+json">'
    '{"@type": "MusicEvent", "name": "Show", "startDate": "2026-11-05T20:00"}'
    "</script>"
)


OPENDATE_URL = "https://app.opendate.io/e/emo-night-brooklyn-november-06-2026-754254"
OPENDATE_PAGE = (Path(__file__).parent / "fixtures" / "opendate_event.html").read_text()


def local(*args):
    return timezone.make_aware(datetime.datetime(*args))


def target(source="ai", **kwargs):
    return {
        "sheet_id": "V0001",
        "name": "The Venue",
        "location": "Burlington, VT",
        "source": source,
        "url": "https://venue.example/",
        "events_page": "https://venue.example/calendar",
        "ical_url": "https://venue.example/cal.ics",
        **kwargs,
    }


def html(url, body):
    return HtmlResponse(url=url, body=body.encode(), encoding="utf-8")


class SpiderTestCase(SimpleTestCase):
    def setUp(self):
        self.results = []
        self.spider = VenueEventsSpider(targets=[], results=self.results)

    def start_requests_for(self, *targets):
        self.spider.targets = list(targets)

        async def collect():
            return [request async for request in self.spider.start()]

        return asyncio.run(collect())

    def test_start_requests_per_source(self):
        callbacks = {
            "ical": self.spider.parse_ical,
            "json-ld": self.spider.parse_json_ld,
            "ticketing": self.spider.parse_ticketing_listing,
            "ai": self.spider.parse_page_for_ai,
        }
        for source, callback in callbacks.items():
            requests = self.start_requests_for(target(source))
            self.assertTrue(all(r.callback == callback for r in requests), source)
        [ical] = self.start_requests_for(target("ical"))
        self.assertEqual(ical.url, "https://venue.example/cal.ics")

    def test_structured_sources_fetch_both_pages_and_ai_fetches_one(self):
        self.assertEqual(
            [r.url for r in self.start_requests_for(target("json-ld"))],
            ["https://venue.example/calendar", "https://venue.example/"],
        )
        self.assertEqual(
            [r.url for r in self.start_requests_for(target("ai"))],
            ["https://venue.example/calendar"],
        )
        # no separate events page: the homepage, once
        self.assertEqual(
            [r.url for r in self.start_requests_for(target("json-ld", events_page=""))],
            ["https://venue.example/"],
        )

    def test_ical_feed_yields_events(self):
        response = TextResponse(url="https://venue.example/cal.ics", body=ICAL.encode())
        list(self.spider.parse_ical(response, target("ical")) or [])
        [result] = self.results
        self.assertEqual(result["kind"], "events")
        self.assertEqual(result["source"], "ical")
        self.assertEqual([e["title"] for e in result["events"]], ["Show"])

    def test_malformed_ical_falls_back_to_ai_on_the_events_page(self):
        response = TextResponse(url="https://venue.example/cal.ics", body=b"garbage")
        with mock.patch.object(spider_module, "parse_ical", side_effect=ValueError("bad tzid")):
            [request] = list(self.spider.parse_ical(response, target("ical")))
        self.assertEqual(request.url, "https://venue.example/calendar")
        self.assertEqual(request.callback, self.spider.parse_page_for_ai)
        [error] = self.results
        self.assertEqual(error["kind"], "error")
        self.assertIn("falling back to ai", error["error"])

    def test_json_ld_page_yields_events(self):
        list(self.spider.parse_json_ld(html("https://venue.example/calendar", JSON_LD_PAGE), target()))
        [result] = self.results
        self.assertEqual((result["kind"], result["source"]), ("events", "json-ld"))
        self.assertEqual(len(result["events"]), 1)

    def test_ticketing_listing_follows_at_most_ten_platform_event_links(self):
        links = "".join(
            f'<a href="https://www.eventbrite.com/e/show-{i}?aff=venue">Show {i}</a>'
            for i in range(12)
        )
        links += '<a href="https://www.eventbrite.com/e/show-0">dupe</a>'
        links += '<a href="https://www.eventbrite.com/o/organizer-1">organizer</a>'
        links += '<a href="/about">About</a>'
        requests = list(
            self.spider.parse_ticketing_listing(html("https://venue.example/", links), target())
        )
        self.assertEqual(len(requests), 10)
        self.assertEqual(requests[0].url, "https://www.eventbrite.com/e/show-0")
        self.assertTrue(all(r.callback == self.spider.parse_ticketing_event for r in requests))

    def test_ticketing_event_with_json_ld(self):
        response = html("https://www.eventbrite.com/e/show-1", JSON_LD_PAGE)
        self.spider.parse_ticketing_event(response, target("ticketing"))
        [result] = self.results
        self.assertEqual((result["kind"], result["source"]), ("events", "ticketing"))

    def ticketing_event(self, url, body):
        self.spider.parse_ticketing_event(html(url, body), target("ticketing"))
        [result] = self.results
        self.results.clear()
        [event] = result["events"]
        return event

    def test_opendate_page_with_a_start_time(self):
        event = self.ticketing_event(OPENDATE_URL, OPENDATE_PAGE)
        self.assertFalse(event["all_day"])
        self.assertEqual(event["starttime"], local(2026, 11, 6, 22, 0))

    def test_opendate_page_without_usable_event_data(self):
        start = '"start_time": "2026-11-06T22:00:00.000-05:00"'
        pages = {
            "no block": OPENDATE_PAGE.replace("js-react-on-rails-component", "something-else"),
            "invalid json": OPENDATE_PAGE.replace('{"confirm"', '{not json "confirm"'),
            "no start_time": OPENDATE_PAGE.replace(start, '"start": "2026-11-06T22:00:00.000-05:00"'),
            "another date": OPENDATE_PAGE.replace(start, '"start_time": "2026-11-07T22:00:00.000-05:00"'),
        }
        for name, page in pages.items():
            with self.subTest(name):
                event = self.ticketing_event(OPENDATE_URL, page)
                self.assertTrue(event["all_day"])
                self.assertEqual(event["starttime"], local(2026, 11, 6, 0, 0))

    def test_full_json_ld_time_is_kept_on_opendate(self):
        page = OPENDATE_PAGE.replace('"startDate": "2026-11-06"', '"startDate": "2026-11-06T21:00:00-05:00"')
        event = self.ticketing_event(OPENDATE_URL, page)
        self.assertEqual(event["starttime"], local(2026, 11, 6, 21, 0))

    def test_other_platforms_pages_are_not_given_opendate_times(self):
        event = self.ticketing_event("https://www.eventbrite.com/e/show-1", OPENDATE_PAGE)
        self.assertTrue(event["all_day"])

    def test_ticketing_event_without_structured_data_goes_to_ai(self):
        response = html("https://app.venuepilot.com/events/1", "<h1>Show</h1><p>Nov 5</p>")
        self.spider.parse_ticketing_event(response, target("ticketing"))
        [result] = self.results
        self.assertEqual(result["kind"], "page")
        self.assertIn("Show", result["text"])

    def test_ai_page_is_capped_and_marked_truncated(self):
        response = html("https://venue.example/", "<p>" + "x" * 100 + "</p>")
        with mock.patch.object(spider_module, "MAX_PAGE_TEXT_LENGTH", 40):
            self.spider.parse_page_for_ai(response, target())
        [result] = self.results
        self.assertEqual(len(result["text"]), 40)
        self.assertTrue(result["truncated"])

    # venue sites whose json-ld gives opendate events a placeholder midnight

    def venue_page(self, *events):
        nodes = [
            {
                "@type": "Event",
                "name": name,
                "startDate": start,
                "url": f"https://thecut.example/events/{i}",
                "offers": {"url": ticket},
            }
            for i, (name, start, ticket) in enumerate(events)
        ]
        response = html(
            "https://thecut.example/events",
            f'<script type="application/ld+json">{json.dumps(nodes)}</script>',
        )
        requests = list(self.spider.parse_json_ld(response, target("json-ld")))
        added = [event for result in self.results for event in result["events"]]
        self.results.clear()
        return requests, added

    def opendate_reply(self, request, page):
        request.callback(html(request.url, page), **request.cb_kwargs)
        [result] = self.results
        self.results.clear()
        [event] = result["events"]
        return result, event

    def test_venue_site_with_an_opendate_ticket_link(self):
        page = OPENDATE_PAGE.replace("22:00:00.000", "20:00:00.000")
        [request], added = self.venue_page(("Roomful of Blues", "2026-11-06T05:00:00Z", OPENDATE_URL))
        self.assertEqual(added, [])
        self.assertEqual(request.url, OPENDATE_URL)

        result, event = self.opendate_reply(request, page)
        self.assertEqual((result["source"], result["url"]), ("json-ld", "https://thecut.example/events"))
        self.assertEqual(event["starttime"], local(2026, 11, 6, 20, 0))
        self.assertFalse(event["all_day"])
        # same identity as the placeholder, so a re-fetch updates the saved event
        _, placeholder = self.opendate_reply(request, "<html></html>")
        self.assertEqual(event["external_id"], placeholder["external_id"])

    def test_opendate_link_without_a_usable_time(self):
        [request], _ = self.venue_page(("Roomful of Blues", "2026-11-06T05:00:00Z", OPENDATE_URL))
        _, event = self.opendate_reply(request, "<html>no data</html>")
        self.assertTrue(event["all_day"])
        self.assertEqual(timezone.localdate(event["starttime"]), datetime.date(2026, 11, 6))

        failure = SimpleNamespace(request=request, value=TimeoutError("took too long"))
        request.errback(failure)
        events_result, error = self.results
        self.assertTrue(events_result["events"][0]["all_day"])
        self.assertEqual(error["kind"], "error")

    def test_placeholder_midnight_without_an_opendate_link_and_real_times(self):
        requests, added = self.venue_page(
            ("No link", "2026-11-06T05:00:00Z", "https://tix.example/1"),
            ("Real time", "2026-11-06T20:00:00-05:00", OPENDATE_URL),
        )
        self.assertEqual(requests, [])
        self.assertEqual([e["title"] for e in added], ["No link", "Real time"])
        self.assertEqual(added[1]["starttime"], local(2026, 11, 6, 20, 0))

    def test_opendate_time_checks_are_capped_per_page(self):
        with mock.patch.object(spider_module, "MAX_OPENDATE_TIME_CHECKS", 2):
            requests, added = self.venue_page(
                *[(f"Show {i}", f"2026-11-{6 + i:02d}T05:00:00Z", f"{OPENDATE_URL}-{i}") for i in range(3)]
            )
        self.assertEqual(len(requests), 2)
        [extra] = added
        self.assertEqual(extra["title"], "Show 2")
        self.assertTrue(extra["all_day"])

    def test_failed_request_is_recorded(self):
        failure = SimpleNamespace(
            request=SimpleNamespace(url="https://venue.example/", cb_kwargs={"target": target()}),
            value=TimeoutError("took too long"),
        )
        self.spider.on_error(failure)
        [result] = self.results
        self.assertEqual(result["kind"], "error")
        self.assertIn("took too long", result["error"])


class PageTextTestCase(SimpleTestCase):
    def test_keeps_text_and_absolute_link_urls(self):
        text = page_text_for_ai(
            """
            <head><title>skip me</title></head>
            <script>var hidden = 1;</script><style>.x{}</style>
            <h1>Shows</h1>
            <a href="/events/42">Tickets</a>
            <a href="mailto:x@venue.example">Email</a>
            <a href="/icon"><img src="i.png"></a>
            """,
            "https://venue.example/",
        )
        self.assertEqual(text, "Shows\nTickets\n<https://venue.example/events/42>\nEmail")

    def test_is_ticketing_event_url(self):
        self.assertTrue(is_ticketing_event_url("https://www.eventbrite.com/e/123"))
        self.assertTrue(is_ticketing_event_url("https://dice.fm/event/abc"))
        self.assertFalse(is_ticketing_event_url("https://www.eventbrite.com/o/organizer"))
        self.assertFalse(is_ticketing_event_url("https://venue.example/events/1"))

    def test_tixr_event_pages_are_not_crawled(self):
        # tixr blocks crawlers by ip, which also locks out people buying tickets
        self.assertFalse(is_ticketing_event_url("https://www.tixr.com/groups/venue/events/show-165144"))

    def test_ticketmaster_event_pages_are_not_crawled(self):
        # ticketmaster refuses crawlers too; its events come from the discovery api
        self.assertFalse(
            is_ticketing_event_url("https://www.ticketmaster.com/punch-brothers-portland-maine-11-11-2026/event/0100649CC7356408")
        )


class CrawlSettingsTestCase(SimpleTestCase):
    def test_crawling_is_polite(self):
        self.assertTrue(SCRAPY_SETTINGS["ROBOTSTXT_OBEY"])
        self.assertTrue(SCRAPY_SETTINGS["AUTOTHROTTLE_ENABLED"])
        self.assertLessEqual(SCRAPY_SETTINGS["CONCURRENT_REQUESTS_PER_DOMAIN"], 2)
        self.assertEqual(SCRAPY_SETTINGS["USER_AGENT"], USER_AGENT)
