import csv
import datetime
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from core.event_fetching.ai_extraction import ExtractionError
from core.event_fetching.spider import VenueEventsSpider
from core.event_fetching.ticketmaster import TicketmasterClient, TicketmasterError
from core.management.commands import fetch_events
from core.models import Event, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from scrapy.http import HtmlResponse

REPORT_COLUMNS = [
    "sheet_id",
    "name",
    "state",
    "city_town",
    "url",
    "events_page",
    "best_source",
    "json_ld_events",
    "ical_url",
    "ical_events",
    "platforms",
    "js_heavy",
    "error",
]


def report_row(sheet_id, best_source, **values):
    row = dict.fromkeys(REPORT_COLUMNS, "")
    row.update(
        sheet_id=sheet_id,
        best_source=best_source,
        url=f"https://{sheet_id.lower()}.example/",
        events_page=f"https://{sheet_id.lower()}.example/calendar",
        **values,
    )
    return row


def event(title, days=7, external_id=None, **values):
    data = {
        "title": title,
        "artists": "",
        "starttime": timezone.now() + datetime.timedelta(days=days),
        "all_day": False,
        "description": "",
        "hyperlink": "",
        "ticket_hyperlink": "",
        "price_amount": None,
        "is_cancelled": False,
        "external_id": external_id or f"ical:{title}",
    }
    data.update(values)
    return data


class FakeCrawlerProcess:
    """stands in for scrapy: start() fills the results list via the test's crawl function"""

    crawl_results = staticmethod(lambda targets: [])
    seen_targets = []

    def __init__(self, settings=None):
        pass

    def crawl(self, spider_class, targets, results):
        self.targets, self.results = targets, results

    def start(self):
        FakeCrawlerProcess.seen_targets = list(self.targets)
        self.results.extend(FakeCrawlerProcess.crawl_results(self.targets))


class FetchEventsTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = os.path.join(self.tmp.name, "event_sources.csv")
        self.venues = {
            sheet_id: Venue.objects.create(sheet_id=sheet_id, name=f"Venue {sheet_id}", state="VT")
            for sheet_id in ("V0001", "V0002", "V0003", "V0004", "V0005", "V0006")
        }
        self.write_report(
            [
                report_row("V0001", "ical", ical_url="https://v0001.example/cal.ics"),
                report_row("V0002", "json-ld", json_ld_events="5"),
                report_row("V0003", "ticketing", platforms="eventbrite"),
                report_row("V0004", "ai-extraction"),
                report_row("V0005", "bot-blocked"),
                report_row("V0006", "social-only"),
            ]
        )
        patcher = mock.patch.object(fetch_events, "CrawlerProcess", FakeCrawlerProcess)
        patcher.start()
        self.addCleanup(patcher.stop)
        FakeCrawlerProcess.crawl_results = staticmethod(lambda targets: [])
        # no real api calls: ai extraction is skipped unless a test sets a key
        env = mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)

    def write_report(self, rows):
        with open(self.report, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def crawl_returns(self, results_for_targets):
        FakeCrawlerProcess.crawl_results = staticmethod(results_for_targets)

    def events_for(self, sheet_id, events, source="ical", url=None):
        def results(targets):
            target = next(t for t in targets if t["sheet_id"] == sheet_id)
            return [
                {
                    "kind": "events",
                    "target": target,
                    "events": events,
                    "url": url or target["url"],
                    "source": source,
                }
            ]

        self.crawl_returns(results)

    def fetch(self, *args):
        out = StringIO()
        call_command("fetch_events", "--report", self.report, *args, stdout=out)
        return out.getvalue()

    def saved(self, sheet_id="V0001"):
        return Event.all_objects.filter(venue=self.venues[sheet_id]).order_by("starttime")

    # selecting venues

    def test_missing_report(self):
        with self.assertRaisesMessage(CommandError, "run check_event_sources first"):
            call_command("fetch_events", "--report", "/nonexistent.csv", stdout=StringIO())

    def test_all_fetches_every_usable_venue(self):
        self.fetch("--all")
        self.assertEqual(
            {t["sheet_id"]: t["source"] for t in FakeCrawlerProcess.seen_targets},
            {"V0001": "ical", "V0002": "json-ld", "V0003": "ticketing", "V0004": "ai"},
        )

    def test_sheet_ids(self):
        self.fetch("--sheet-ids", "V0002,V0004")
        self.assertEqual(
            sorted(t["sheet_id"] for t in FakeCrawlerProcess.seen_targets), ["V0002", "V0004"]
        )

    def test_pilot_picks_a_few_likely_venues_per_source(self):
        for sheet_id in ("V0011", "V0012", "V0013", "V0014"):
            Venue.objects.create(sheet_id=sheet_id, name=sheet_id)
        self.write_report(
            [
                report_row("V0011", "json-ld", json_ld_events="1"),
                report_row("V0012", "json-ld", json_ld_events="9"),
                report_row("V0013", "json-ld", json_ld_events="9"),
                report_row("V0014", "ai-extraction", js_heavy="yes"),
                report_row("V0004", "ai-extraction"),
            ]
        )
        self.fetch("--per-source", "1")
        # too few json-ld events and js-heavy pages are passed over for the pilot
        self.assertEqual(
            [t["sheet_id"] for t in FakeCrawlerProcess.seen_targets], ["V0012", "V0004"]
        )

    def test_no_venues_to_fetch(self):
        with self.assertRaisesMessage(CommandError, "no venues to fetch"):
            self.fetch("--sheet-ids", "V0005")

    # saving

    def test_new_events_are_saved_unapproved(self):
        self.events_for(
            "V0001",
            [event("Show", external_id="ical:abc"), event("Fest", all_day=True)],
            url="https://v0001.example/cal.ics",
        )
        output = self.fetch("--sheet-ids", "V0001")
        show = Event.all_objects.get(external_id="ical:abc")
        self.assertFalse(show.is_approved)
        self.assertEqual(show.source, "ical")
        self.assertEqual(show.source_url, "https://v0001.example/cal.ics")
        self.assertIsNone(show.starttime_override)
        self.assertEqual(Event.all_objects.get(title="Fest").starttime_override, "time TBA")
        # unapproved events don't show on the site
        self.assertFalse(Event.objects.filter(external_id="ical:abc").exists())
        self.assertIn("2 created", output)

    def test_past_events_are_not_saved(self):
        self.events_for("V0001", [event("Last month", days=-30), event("Next week")])
        self.fetch("--sheet-ids", "V0001")
        self.assertEqual([e.title for e in self.saved()], ["Next week"])

    def test_events_found_twice_are_saved_once(self):
        self.events_for("V0001", [event("Show", external_id="x"), event("Show", external_id="x")])
        self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.saved().count(), 1)

    def test_at_most_50_soonest_events_per_venue(self):
        self.events_for(
            "V0001", [event(f"Show {i}", days=i + 1) for i in reversed(range(60))]
        )
        self.fetch("--sheet-ids", "V0001")
        saved = self.saved()
        self.assertEqual(saved.count(), fetch_events.MAX_EVENTS_PER_VENUE)
        self.assertEqual(saved.last().title, "Show 49")

    def test_rerun_updates_without_duplicates_and_keeps_approval(self):
        self.events_for("V0001", [event("Show", external_id="ical:abc", description="old")])
        self.fetch("--sheet-ids", "V0001")
        Event.all_objects.filter(external_id="ical:abc").update(is_approved=True)

        self.events_for("V0001", [event("Show", external_id="ical:abc", description="new")])
        output = self.fetch("--sheet-ids", "V0001")

        show = Event.all_objects.get(external_id="ical:abc")
        self.assertEqual(show.description, "new")
        self.assertTrue(show.is_approved)
        self.assertEqual(self.saved().count(), 1)
        self.assertIn("1 updated", output)

    def test_opendate_time_filled_in_on_a_refetch(self):
        # the real opendate page, moved a month ahead so the event is always upcoming
        page = (Path(__file__).parent / "fixtures" / "opendate_event.html").read_text()
        day = timezone.localdate() + datetime.timedelta(days=30)
        page = page.replace("2026-11-06", day.isoformat())
        url = "https://app.opendate.io/e/emo-night-brooklyn-november-06-2026-754254"

        def parsed(body):
            results = []
            spider = VenueEventsSpider(targets=[], results=results)
            response = HtmlResponse(url=url, body=body.encode(), encoding="utf-8")
            spider.parse_ticketing_event(response, {"sheet_id": "V0001"})
            return results[0]["events"]

        self.events_for("V0001", parsed(page.replace("js-react-on-rails-component", "x")), source="ticketing")
        self.fetch("--sheet-ids", "V0001")
        [before] = self.saved()
        self.assertEqual(before.starttime_override, "time TBA")

        self.events_for("V0001", parsed(page), source="ticketing")
        output = self.fetch("--sheet-ids", "V0001")
        [after] = self.saved()
        self.assertEqual(after.pk, before.pk)
        self.assertEqual(after.external_id, before.external_id)
        self.assertIsNone(after.starttime_override)
        self.assertEqual(timezone.localtime(after.starttime).date(), day)
        self.assertNotEqual(timezone.localtime(after.starttime).hour, 0)
        self.assertIn("1 updated", output)

    def test_events_without_title_or_artists_are_skipped(self):
        self.events_for("V0001", [event("", external_id="blank")])
        self.fetch("--sheet-ids", "V0001")
        self.assertFalse(self.saved().exists())

    def test_imported_content_is_made_safe(self):
        self.events_for(
            "V0001",
            [
                event(
                    "Show",
                    description="<script>alert(1)</script>",
                    hyperlink="https://venue.example/" + "x" * 300,
                    is_cancelled=True,
                    price_amount=35,
                )
            ],
        )
        self.fetch("--sheet-ids", "V0001")
        show = self.saved().get()
        self.assertNotIn("<script>", show.description)
        self.assertIn("&lt;script&gt;", show.description)
        self.assertIsNone(show.hyperlink)
        self.assertTrue(show.is_cancelled)
        self.assertEqual(show.price, "$$")

    def test_failed_request_is_reported_and_others_still_saved(self):
        def results(targets):
            by_id = {t["sheet_id"]: t for t in targets}
            return [
                {
                    "kind": "error",
                    "target": by_id["V0001"],
                    "url": "https://v0001.example/cal.ics",
                    "error": "TimeoutError()",
                },
                {
                    "kind": "events",
                    "target": by_id["V0002"],
                    "events": [event("Elsewhere")],
                    "url": "https://v0002.example/",
                    "source": "json-ld",
                },
            ]

        self.crawl_returns(results)
        output = self.fetch("--sheet-ids", "V0001,V0002")
        self.assertIn("failed: https://v0001.example/cal.ics TimeoutError()", output)
        self.assertTrue(self.saved("V0002").exists())

    def test_dry_run_saves_nothing(self):
        self.events_for("V0001", [event("Show")])
        output = self.fetch("--sheet-ids", "V0001", "--dry-run")
        self.assertFalse(self.saved().exists())
        self.assertIn("[dry run] 1 created", output)

    # ai extraction

    def ai_page(self, *sheet_ids):
        def results(targets):
            return [
                {
                    "kind": "page",
                    "target": t,
                    "url": t["events_page"],
                    "text": "page text",
                    "truncated": False,
                }
                for t in targets
                if t["sheet_id"] in sheet_ids
            ]

        self.crawl_returns(results)

    def test_ai_skipped_without_api_key(self):
        self.ai_page("V0004")
        output = self.fetch("--sheet-ids", "V0004")
        self.assertIn("ai extraction skipped (no ANTHROPIC_API_KEY)", output)

    def test_truncated_page_is_noted(self):
        def results(targets):
            [target] = targets
            return [
                {"kind": "page", "target": target, "url": target["url"], "text": "x", "truncated": True}
            ]

        self.crawl_returns(results)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), mock.patch(
            "anthropic.Anthropic"
        ), mock.patch(
            "core.event_fetching.ai_extraction.extract_events",
            return_value=([], mock.Mock(input_tokens=1, output_tokens=1)),
        ):
            output = self.fetch("--sheet-ids", "V0004")
        self.assertIn("page text was truncated for ai extraction", output)

    def test_ai_skipped_with_flag(self):
        self.ai_page("V0004")
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}):
            output = self.fetch("--sheet-ids", "V0004", "--skip-ai")
        self.assertIn("ai extraction skipped (--skip-ai)", output)

    def test_ai_failure_for_one_page_doesnt_stop_others(self):
        Venue.objects.create(sheet_id="V0007", name="Venue V0007")
        self.write_report(
            [report_row("V0004", "ai-extraction"), report_row("V0007", "ai-extraction")]
        )
        self.ai_page("V0004", "V0007")

        def fake_extract(client, name, location, url, text, model):
            if name == "Venue V0004":
                raise ExtractionError("stopped with max_tokens")
            usage = mock.Mock(input_tokens=1000, output_tokens=200)
            return [event("AI show", external_id="ai:1")], usage

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), mock.patch(
            "anthropic.Anthropic"
        ), mock.patch("core.event_fetching.ai_extraction.extract_events", fake_extract):
            output = self.fetch("--sheet-ids", "V0004,V0007", "--model", "claude-opus-5-5")

        self.assertIn("ai extraction failed: stopped with max_tokens", output)
        self.assertFalse(self.saved("V0004").exists())
        saved = Event.all_objects.get(external_id="ai:1")
        self.assertEqual(saved.source, "ai")
        self.assertEqual(saved.source_url, "https://v0007.example/calendar")
        self.assertIn("ai (claude-opus-5-5): 1000 input / 200 output tokens", output)
        self.assertIn("ai extraction used 1000 input / 200 output tokens", output)


def tm_event(id, name="Show", days=7, segment="Music", **changes):
    """a discovery api event, starting `days` from now"""
    start = timezone.localtime(timezone.now() + datetime.timedelta(days=days))
    event = {
        "id": id,
        "name": name,
        "url": f"https://www.ticketmaster.com/event/{id}",
        "dates": {
            "start": {
                "localDate": start.date().isoformat(),
                "localTime": "20:00:00",
            },
            "status": {"code": "onsale"},
        },
        "classifications": [{"primary": True, "segment": {"name": segment}}],
        "priceRanges": [{"min": 25.0}],
        "_embedded": {"attractions": [{"name": name}, {"name": "Support Act"}]},
    }
    event.update(changes)
    return event


class FetchEventsTicketmasterTestCase(TestCase):
    """fetch_events with venues linked to ticketmaster"""

    def setUp(self):
        FetchEventsTestCase.setUp(self)
        # link a venue of every kind: ical, json-ld, ticketing, ai and bot-blocked
        for sheet_id in ("V0001", "V0002", "V0003", "V0004", "V0005"):
            Venue.objects.filter(sheet_id=sheet_id).update(ticketmaster_venue_id=f"tm-{sheet_id}")
        self.venues = {v.sheet_id: v for v in Venue.objects.all()}
        env = mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": "tm-key"})
        env.start()
        self.addCleanup(env.stop)
        FakeCrawlerProcess.seen_targets = []
        self.tm_events = {}
        self.tm_requests = []

        def venue_events(client, venue_id):
            self.tm_requests.append(venue_id)
            events = self.tm_events.get(venue_id, [])
            if isinstance(events, Exception):
                raise events
            return events

        patcher = mock.patch.object(TicketmasterClient, "venue_events", venue_events)
        patcher.start()
        self.addCleanup(patcher.stop)

    # reuse the helpers of the other test case
    write_report = FetchEventsTestCase.write_report
    crawl_returns = FetchEventsTestCase.crawl_returns
    fetch = FetchEventsTestCase.fetch
    saved = FetchEventsTestCase.saved

    def sources(self, *args):
        return {
            target["sheet_id"]: target["source"]
            for target in fetch_events.select_targets(self.report, 3, *args)
        }

    def test_linked_venues_keep_feeds_and_replace_scraping(self):
        self.assertEqual(
            self.sources(None, True),
            {
                # ticketmaster replaces the ical feed, but not json-ld
                "V0001": "ticketmaster",
                "V0002": "json-ld",
                "V0003": "ticketmaster",
                "V0004": "ticketmaster",
                # bot-blocked in the report, but the api still works
                "V0005": "ticketmaster",
            },
        )

    def test_sheet_ids_include_linked_venues_missing_from_the_report(self):
        Venue.objects.create(sheet_id="V0099", name="Unreported", ticketmaster_venue_id="tm-99")
        self.assertEqual(self.sources({"V0099", "V0006"}, False), {"V0099": "ticketmaster"})

    def test_inactive_linked_venues_are_left_out_of_all(self):
        Venue.objects.create(
            sheet_id="V0098", name="Closed", ticketmaster_venue_id="tm-98", is_active=False
        )
        self.assertNotIn("V0098", self.sources(None, True))

    def test_skip_ticketmaster_uses_the_report_sources(self):
        targets = fetch_events.select_targets(self.report, 3, None, True, use_ticketmaster=False)
        self.assertEqual(
            {t["sheet_id"]: t["source"] for t in targets},
            {"V0001": "ical", "V0002": "json-ld", "V0003": "ticketing", "V0004": "ai"},
        )

    def test_pilot_switches_linked_venues_too(self):
        self.assertEqual(self.sources(None, False)["V0003"], "ticketmaster")

    def test_events_are_saved_unapproved_from_the_api(self):
        self.tm_events["tm-V0003"] = [tm_event("ev1", "Samantha Fish")]
        output = self.fetch("--sheet-ids", "V0003")
        event = Event.all_objects.get(external_id="tm:ev1")
        self.assertFalse(event.is_approved)
        self.assertEqual(event.source, "ticketmaster")
        self.assertEqual(event.source_url, "https://www.ticketmaster.com/event/ev1")
        self.assertEqual(event.venue, self.venues["V0003"])
        self.assertEqual((event.title, event.artists, event.price), ("Samantha Fish", "Support Act", "$"))
        self.assertEqual(event.ticket_hyperlink, "https://www.ticketmaster.com/event/ev1")
        self.assertEqual(self.tm_requests, ["tm-V0003"])
        # nothing left to crawl
        self.assertEqual(FakeCrawlerProcess.seen_targets, [])
        self.assertIn("[ticketmaster]", output)
        self.assertIn("1 created", output)

    def test_reimport_updates_and_keeps_approval(self):
        self.tm_events["tm-V0003"] = [tm_event("ev1", "Old Name")]
        self.fetch("--sheet-ids", "V0003")
        Event.all_objects.filter(external_id="tm:ev1").update(is_approved=True)
        self.tm_events["tm-V0003"] = [tm_event("ev1", "New Name", days=9)]
        self.fetch("--sheet-ids", "V0003")
        event = Event.all_objects.get(external_id="tm:ev1")
        self.assertEqual(event.title, "New Name")
        self.assertTrue(event.is_approved)
        self.assertEqual(Event.all_objects.filter(external_id="tm:ev1").count(), 1)

    def test_cancelled_event(self):
        event = tm_event("ev1")
        event["dates"]["status"]["code"] = "canceled"
        self.tm_events["tm-V0003"] = [event]
        self.fetch("--sheet-ids", "V0003")
        self.assertTrue(Event.all_objects.get(external_id="tm:ev1").is_cancelled)

    def test_non_music_events_are_left_out_with_a_note(self):
        self.tm_events["tm-V0003"] = [tm_event("ev1"), tm_event("ev2", segment="Sports")]
        output = self.fetch("--sheet-ids", "V0003")
        self.assertTrue(Event.all_objects.filter(external_id="tm:ev1").exists())
        self.assertFalse(Event.all_objects.filter(external_id="tm:ev2").exists())
        self.assertIn("ticketmaster: 1 non-music or undated events left out", output)

    def test_dry_run_saves_nothing(self):
        self.tm_events["tm-V0003"] = [tm_event("ev1")]
        output = self.fetch("--sheet-ids", "V0003", "--dry-run")
        self.assertFalse(Event.all_objects.filter(external_id="tm:ev1").exists())
        self.assertIn("[dry run] 1 created", output)

    def test_no_api_key(self):
        with mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": ""}):
            output = self.fetch("--sheet-ids", "V0002,V0003")
        self.assertEqual(self.tm_requests, [])
        self.assertIn("ticketmaster skipped (no TICKETMASTER_API_KEY)", output)
        # the json-ld venue is still crawled
        self.assertEqual([t["sheet_id"] for t in FakeCrawlerProcess.seen_targets], ["V0002"])

    def ical_event(self, title, days=7, approved=False, source="ical"):
        return Event.all_objects.create(
            title=title,
            starttime=timezone.now() + datetime.timedelta(days=days),
            venue=self.venues["V0001"],
            source=source,
            external_id=f"{source}:{title}",
            is_approved=approved,
        )

    def test_switching_from_ical_removes_unapproved_feed_events(self):
        stale = [self.ical_event(f"feed show {i}") for i in range(3)]
        approved = self.ical_event("approved feed show", approved=True)
        past = self.ical_event("last month", days=-30)
        eventbrite = self.ical_event("eventbrite show", source="ticketing")
        self.tm_events["tm-V0001"] = [tm_event("ev1")]

        output = self.fetch("--sheet-ids", "V0001")

        self.assertFalse(Event.all_objects.filter(pk__in=[e.pk for e in stale]).exists())
        for kept in (approved, past, eventbrite):
            self.assertTrue(Event.all_objects.filter(pk=kept.pk).exists(), kept.title)
        self.assertTrue(Event.all_objects.filter(external_id="tm:ev1").exists())
        self.assertIn("removed 3 unapproved events from the venue's ical feed", output)

    def test_feed_events_kept_on_dry_run_and_api_failure(self):
        stale = self.ical_event("feed show")
        self.tm_events["tm-V0001"] = [tm_event("ev1")]
        self.fetch("--sheet-ids", "V0001", "--dry-run")
        self.assertTrue(Event.all_objects.filter(pk=stale.pk).exists())

        self.tm_events["tm-V0001"] = TicketmasterError("events.json: HTTP 503")
        self.fetch("--sheet-ids", "V0001")
        self.assertTrue(Event.all_objects.filter(pk=stale.pk).exists())

    def test_api_failure_for_one_venue_doesnt_stop_others(self):
        self.tm_events["tm-V0003"] = TicketmasterError("events.json: HTTP 503")
        self.tm_events["tm-V0004"] = [tm_event("ev4")]
        output = self.fetch("--sheet-ids", "V0003,V0004")
        self.assertIn("ticketmaster failed: events.json: HTTP 503", output)
        self.assertTrue(Event.all_objects.filter(external_id="tm:ev4").exists())

    def test_skip_ticketmaster_flag(self):
        self.fetch("--sheet-ids", "V0003", "--skip-ticketmaster")
        self.assertEqual(self.tm_requests, [])
        self.assertEqual(
            [(t["sheet_id"], t["source"]) for t in FakeCrawlerProcess.seen_targets],
            [("V0003", "ticketing")],
        )


class FetchEventsLabellingTestCase(TestCase):
    """fetch_events labelling events by kind before saving them"""

    write_report = FetchEventsTestCase.write_report
    crawl_returns = FetchEventsTestCase.crawl_returns
    events_for = FetchEventsTestCase.events_for
    fetch = FetchEventsTestCase.fetch
    saved = FetchEventsTestCase.saved

    def setUp(self):
        FetchEventsTestCase.setUp(self)
        env = mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"})
        env.start()
        self.addCleanup(env.stop)
        anthropic_client = mock.patch("anthropic.Anthropic")
        anthropic_client.start()
        self.addCleanup(anthropic_client.stop)
        self.labelled = []
        self.labels = {}
        self.errors = []

        def classify(client, items, model):
            self.labelled.append([item["title"] for item in items])
            kinds = [self.labels.get(item["title"], "live_music") for item in items]
            return kinds, self.errors, (len(items) * 50, len(items) * 5)

        patcher = mock.patch.object(fetch_events, "classify", classify)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_new_events_are_labelled_before_saving(self):
        self.labels = {"Trivia Night": "other", "DJ Night": "dj_dance"}
        self.events_for(
            "V0001", [event("Band"), event("Trivia Night"), event("DJ Night")]
        )
        output = self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.labelled, [["Band", "Trivia Night", "DJ Night"]])
        saved = {e.title: (e.kind, e.kind_set_by) for e in self.saved()}
        self.assertEqual(
            saved,
            {
                "Band": ("live_music", "ai"),
                "Trivia Night": ("other", "ai"),
                "DJ Night": ("dj_dance", "ai"),
            },
        )
        self.assertIn("not music, hidden from review (1): Trivia Night [other]", output)
        self.assertIn("kinds: 1 dj_dance, 1 live_music, 1 other (1 not music, hidden from review)", output)
        self.assertIn("labelling used 150 input / 15 output tokens", output)

    def test_venue_is_given_to_the_labeller(self):
        captured = []
        with mock.patch.object(
            fetch_events, "classify", lambda client, items, model: captured.extend(items) or (["live_music"] * len(items), [], (0, 0))
        ):
            self.events_for("V0001", [event("Band")])
            self.fetch("--sheet-ids", "V0001")
        self.assertEqual(captured[0]["venue"], "Venue V0001 (VT)")

    def test_reimport_makes_no_labelling_request(self):
        self.events_for("V0001", [event("Band", external_id="ical:band")])
        self.fetch("--sheet-ids", "V0001")
        self.labelled.clear()
        self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.labelled, [])
        self.assertEqual(Event.all_objects.get(external_id="ical:band").kind, "live_music")

    def test_unlabelled_existing_event_gets_labelled(self):
        self.events_for("V0001", [event("Band", external_id="ical:band")])
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            self.fetch("--sheet-ids", "V0001")
        self.assertEqual(Event.all_objects.get(external_id="ical:band").kind, "")
        self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.labelled, [["Band"]])
        self.assertEqual(Event.all_objects.get(external_id="ical:band").kind, "live_music")

    def test_admin_label_survives(self):
        self.events_for("V0001", [event("Band", external_id="ical:band")])
        self.fetch("--sheet-ids", "V0001")
        Event.all_objects.filter(external_id="ical:band").update(kind="other", kind_set_by="admin")
        self.labelled.clear()
        self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.labelled, [])
        event_ = Event.all_objects.get(external_id="ical:band")
        self.assertEqual((event_.kind, event_.kind_set_by), ("other", "admin"))

    def test_no_api_key_saves_unlabelled(self):
        self.events_for("V0001", [event("Band"), event("Trivia")])
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            output = self.fetch("--sheet-ids", "V0001")
        self.assertEqual(self.labelled, [])
        self.assertEqual({e.kind for e in self.saved()}, {""})
        self.assertIn("2 events left unlabelled (no ANTHROPIC_API_KEY)", output)
        self.assertIn("kinds: 2 unlabelled (0 not music, hidden from review)", output)

    def test_skip_ai_saves_unlabelled(self):
        self.events_for("V0001", [event("Band")])
        output = self.fetch("--sheet-ids", "V0001", "--skip-ai")
        self.assertEqual(self.labelled, [])
        self.assertIn("1 events left unlabelled (--skip-ai)", output)

    def test_ai_extracted_events_keep_their_own_kind(self):
        self.events_for(
            "V0004",
            [event("Improv Night", external_id="ai:1", kind="comedy"), event("Mystery", external_id="ai:2")],
            source="ai",
        )
        self.fetch("--sheet-ids", "V0004")
        self.assertEqual(self.labelled, [])
        self.assertEqual(Event.all_objects.get(external_id="ai:1").kind, "comedy")
        self.assertEqual(Event.all_objects.get(external_id="ai:2").kind, "")

    def test_admin_label_survives_an_extracted_kind(self):
        self.events_for("V0004", [event("Improv Night", external_id="ai:1", kind="comedy")], source="ai")
        self.fetch("--sheet-ids", "V0004")
        Event.all_objects.filter(external_id="ai:1").update(kind="live_music", kind_set_by="admin")
        self.fetch("--sheet-ids", "V0004")
        self.assertEqual(Event.all_objects.get(external_id="ai:1").kind, "live_music")

    def test_failed_labelling_is_reported(self):
        self.errors = ["labelling events 1-1 failed: overloaded"]
        self.events_for("V0001", [event("Band")])
        output = self.fetch("--sheet-ids", "V0001")
        self.assertIn("labelling events 1-1 failed: overloaded", output)

    def test_dry_run_labels_but_saves_nothing(self):
        self.labels = {"Trivia": "other"}
        self.events_for("V0001", [event("Trivia")])
        output = self.fetch("--sheet-ids", "V0001", "--dry-run")
        self.assertFalse(self.saved().exists())
        self.assertIn("not music, hidden from review (1): Trivia [other]", output)


class PriceBucketTestCase(SimpleTestCase):
    def test_boundaries(self):
        cases = {
            None: None,
            0: "🌀 free",
            0.01: "$",
            29.99: "$",
            30: "$$",
            49.99: "$$",
            50: "$$$",
            74.99: "$$$",
            75: "$$$$",
            250: "$$$$",
        }
        for amount, bucket in cases.items():
            self.assertEqual(fetch_events.price_bucket(amount), bucket, amount)
