import datetime
import json
from types import SimpleNamespace
from unittest import mock

from core.event_fetching.ai_extraction import (
    MODEL,
    SYSTEM_PROMPT,
    ExtractionError,
    extract_events,
    extract_events_in_parts,
    parse_price,
    split_text,
)
from core.event_fetching.kinds import KINDS
from django.test import SimpleTestCase
from django.utils import timezone

PAGE_URL = "https://venue.example/calendar"


def raw_event(**fields):
    event = dict.fromkeys(
        ["title", "artists", "start_date", "start_time", "url", "ticket_url", "price", "description", "kind"],
        "",
    )
    event.update(fields)
    return event


def fake_client(events, stop_reason="end_turn"):
    client = mock.Mock()
    client.beta.messages.create.return_value = SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=json.dumps({"events": events}))],
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
    )
    return client


class ExtractEventsTestCase(SimpleTestCase):
    def run_extraction(self, events, stop_reason="end_turn", **kwargs):
        client = fake_client(events, stop_reason)
        result = extract_events(
            client, "The Venue", "Burlington, VT", PAGE_URL, "page text", **kwargs
        )
        return result, client.beta.messages.create.call_args.kwargs

    def test_maps_events(self):
        (events, usage), _ = self.run_extraction(
            [
                raw_event(
                    title="Samantha Fish",
                    artists="Sgt. Splendor",
                    start_date="2026-11-05",
                    start_time="20:00",
                    url="https://venue.example/e/sf",
                    ticket_url="https://tix.example/sf",
                    price="$20 adv / $25 door",
                    description="Blues &amp; rock",
                )
            ]
        )
        [event] = events
        self.assertEqual(event["title"], "Samantha Fish")
        self.assertEqual(event["artists"], "Sgt. Splendor")
        self.assertEqual(
            event["starttime"], timezone.make_aware(datetime.datetime(2026, 11, 5, 20, 0))
        )
        self.assertFalse(event["all_day"])
        self.assertEqual(event["hyperlink"], "https://venue.example/e/sf")
        self.assertEqual(event["ticket_hyperlink"], "https://tix.example/sf")
        self.assertEqual(event["price_amount"], 20.0)
        self.assertEqual(event["description"], "Blues & rock")
        self.assertTrue(event["external_id"].startswith("ai:"))
        self.assertEqual(usage.input_tokens, 1000)

    def test_missing_or_invalid_time_means_all_day(self):
        (events, _), _ = self.run_extraction(
            [
                raw_event(title="A", start_date="2026-11-05"),
                raw_event(title="B", start_date="2026-11-06", start_time="8pm"),
            ]
        )
        self.assertTrue(all(event["all_day"] for event in events))
        self.assertEqual(events[0]["hyperlink"], PAGE_URL)

    def test_invalid_dates_and_placeholders_are_dropped(self):
        (events, _), _ = self.run_extraction(
            [
                raw_event(title="TBD show", start_date="TBD"),
                raw_event(title="No Event Tonight", start_date="2026-11-05"),
                raw_event(title="Real", start_date="2026-11-05"),
            ]
        )
        self.assertEqual([event["title"] for event in events], ["Real"])

    def test_page_with_no_events(self):
        (events, _), _ = self.run_extraction([])
        self.assertEqual(events, [])

    def test_repeated_nights_without_links_get_distinct_ids(self):
        (events, _), _ = self.run_extraction(
            [raw_event(title="Jazz Jam", start_date=f"2026-11-{day}") for day in ("05", "12", "19")]
        )
        self.assertEqual(len({event["external_id"] for event in events}), 3)

    def test_ids_are_stable_across_runs(self):
        raw = [raw_event(title="Show", start_date="2026-11-05", url="https://venue.example/e/1")]
        (first, _), _ = self.run_extraction(raw)
        (second, _), _ = self.run_extraction(raw)
        self.assertEqual(first[0]["external_id"], second[0]["external_id"])

    def test_output_cut_off_raises(self):
        with self.assertRaises(ExtractionError):
            self.run_extraction([raw_event(title="A", start_date="2026-11-05")], "max_tokens")

    def test_request_uses_default_model_and_todays_date(self):
        _, request = self.run_extraction([])
        self.assertEqual(request["model"], MODEL)
        self.assertEqual(MODEL, "claude-haiku-5-5")
        self.assertEqual(request["output_config"]["format"]["type"], "json_schema")
        content = request["messages"][0]["content"]
        self.assertIn(f"Today's date: {timezone.localdate().isoformat()}", content)
        self.assertIn("Venue: The Venue (Burlington, VT)", content)
        self.assertIn("<page_text>\npage text\n</page_text>", content)
        self.assertNotIn("fallbacks", request)

    def test_fallbacks_only_for_models_that_support_them(self):
        for model in ("claude-opus-5-5", "claude-sonnet-5-5"):
            _, request = self.run_extraction([], model=model)
            self.assertEqual(request["model"], model)
            self.assertEqual(request["fallbacks"], "default")
        _, request = self.run_extraction([], model="claude-haiku-5-5")
        self.assertNotIn("betas", request)

    def test_prompt_rules(self):
        # the model is told how to fill the year and not to guess
        self.assertIn("on or after today", SYSTEM_PROMPT)
        self.assertIn("rather than guessing", SYSTEM_PROMPT)
        self.assertIn("Leave out past events", SYSTEM_PROMPT)


class ExtractedKindTestCase(SimpleTestCase):
    run_extraction = ExtractEventsTestCase.run_extraction

    def test_events_carry_their_kind(self):
        (events, _), request = self.run_extraction(
            [
                raw_event(title="IMPROV COMEDY: an evening of laughs", start_date="2026-11-05", kind="comedy"),
                raw_event(title="Samantha Fish", artists="Sgt. Splendor", start_date="2026-11-06", kind="live_music"),
            ]
        )
        self.assertEqual([e["kind"] for e in events], ["comedy", "live_music"])
        item = request["output_config"]["format"]["schema"]["properties"]["events"]["items"]
        self.assertEqual(item["properties"]["kind"]["enum"], KINDS)
        self.assertIn("kind", item["required"])
        self.assertIn("only when a band, artist or DJ is named", request["system"])

    def test_unknown_kind_leaves_the_event_unlabelled(self):
        (events, _), _ = self.run_extraction(
            [raw_event(title="Show", start_date="2026-11-05", kind="polka"), raw_event(title="Other", start_date="2026-11-06")]
        )
        self.assertEqual([e["kind"] for e in events], ["", ""])


class ParsePriceTestCase(SimpleTestCase):
    def test_parse_price(self):
        self.assertEqual(parse_price("$15"), 15.0)
        self.assertEqual(parse_price("$20 adv / $25 door"), 20.0)
        self.assertEqual(parse_price("Free"), 0.0)
        self.assertEqual(parse_price("free with RSVP"), 0.0)
        self.assertEqual(parse_price("$12.50"), 12.5)
        self.assertIsNone(parse_price(""))
        self.assertIsNone(parse_price("donation"))


def long_page(paragraphs=8):
    return "\n\n".join(f"show {i}: " + "x" * 600 for i in range(paragraphs))


class ExtractInPartsTestCase(SimpleTestCase):
    """a page listing more events than fit in one response is extracted in halves"""

    def run_parts(self, responder, page_text, **kwargs):
        calls = []

        def fake_extract(client, name, location, url, text, model):
            calls.append(text)
            return responder(text)

        with mock.patch("core.event_fetching.ai_extraction.extract_events", fake_extract):
            result = extract_events_in_parts(
                None, "The Burren", "Somerville, MA", PAGE_URL, page_text, **kwargs
            )
        return result, calls

    @staticmethod
    def usage(input_tokens, output_tokens):
        return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)

    def test_overflowing_page_is_split_and_merged(self):
        page = long_page()

        def responder(text):
            if text == page:
                raise ExtractionError("stopped with max_tokens", usage=self.usage(500, 16000))
            # each half finds its own show, and both find a show listed at the seam
            own = {"external_id": text[:7], "title": text[:7]}
            shared = {"external_id": "seam", "title": "Seam Show"}
            return [own, shared], self.usage(300, 100)

        (events, usage), calls = self.run_parts(responder, page)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1] + calls[2], page)
        self.assertEqual(sorted(e["external_id"] for e in events), sorted([calls[1][:7], calls[2][:7], "seam"]))
        # the failed first request counts too
        self.assertEqual((usage.input_tokens, usage.output_tokens), (1100, 16200))

    def test_gives_up_after_max_splits(self):
        def responder(text):
            raise ExtractionError("stopped with max_tokens", usage=self.usage(1, 1))

        with self.assertRaisesMessage(ExtractionError, "max_tokens"):
            self.run_parts(responder, long_page(), splits_left=1)

    def test_other_errors_and_short_pages_are_not_split(self):
        def refused(text):
            raise ExtractionError("stopped with refusal")

        with self.assertRaisesMessage(ExtractionError, "refusal"):
            self.run_parts(refused, long_page())

        def overflow(text):
            raise ExtractionError("stopped with max_tokens")

        with self.assertRaisesMessage(ExtractionError, "max_tokens"):
            _, calls = self.run_parts(overflow, "a short page")

    def test_page_that_fits_is_one_request(self):
        (events, _), calls = self.run_parts(
            lambda text: ([{"external_id": "a"}], self.usage(10, 10)), long_page()
        )
        self.assertEqual(len(calls), 1)

    def test_split_text_cuts_at_a_paragraph_break(self):
        first, second = split_text("aaaa\n\nbbbb\ncccc")
        self.assertEqual(first, "aaaa")
        self.assertEqual(second, "\n\nbbbb\ncccc")
        self.assertEqual("".join(split_text("no breaks at all")), "no breaks at all")
