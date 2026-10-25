import asyncio
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
        self.spider.parse_json_ld(html("https://venue.example/calendar", JSON_LD_PAGE), target())
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


class CrawlSettingsTestCase(SimpleTestCase):
    def test_crawling_is_polite(self):
        self.assertTrue(SCRAPY_SETTINGS["ROBOTSTXT_OBEY"])
        self.assertTrue(SCRAPY_SETTINGS["AUTOTHROTTLE_ENABLED"])
        self.assertLessEqual(SCRAPY_SETTINGS["CONCURRENT_REQUESTS_PER_DOMAIN"], 2)
        self.assertEqual(SCRAPY_SETTINGS["USER_AGENT"], USER_AGENT)
