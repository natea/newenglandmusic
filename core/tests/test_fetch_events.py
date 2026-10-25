import csv
import datetime
import os
import tempfile
from io import StringIO
from unittest import mock

from core.event_fetching.ai_extraction import ExtractionError
from core.management.commands import fetch_events
from core.models import Event, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

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
