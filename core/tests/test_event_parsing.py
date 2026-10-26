import datetime
import json

from core.event_fetching.parsing import (
    MAX_DESCRIPTION_LENGTH,
    clean_description,
    clean_text,
    is_placeholder,
    is_placeholder_midnight,
    opendate_start_time,
    parse_ical,
    parse_json_ld,
    split_merged_timezones,
    stable_id,
)
from pathlib import Path

from django.test import SimpleTestCase
from django.utils import timezone

OPENDATE_PAGE = (Path(__file__).parent / "fixtures" / "opendate_event.html").read_text()


def ical(*events):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//EN"]
    for event in events:
        lines += ["BEGIN:VEVENT", *event, "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines).encode()


def local(*args):
    return timezone.make_aware(datetime.datetime(*args))


# as luthier's co-op's events calendar feed sends it: two timezones in one block
MERGED_TIMEZONES = [
    "BEGIN:VTIMEZONE",
    "TZID:America/New_York",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0400",
    "TZOFFSETTO:-0500",
    "TZNAME:EST",
    "DTSTART:20261101T060000",
    "END:STANDARD",
    "TZID:America/Halifax",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0300",
    "TZOFFSETTO:-0400",
    "TZNAME:AST",
    "DTSTART:20261101T050000",
    "END:STANDARD",
    "END:VTIMEZONE",
]


class MergedTimezonesTestCase(SimpleTestCase):
    def feed(self):
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//EN", *MERGED_TIMEZONES]
        lines += [
            "BEGIN:VEVENT",
            "UID:open-mic",
            "SUMMARY:Open Mic",
            "DTSTART;TZID=America/New_York:20261127T190000",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        return "\r\n".join(lines).encode()

    def test_feed_with_merged_timezones_parses(self):
        [event] = parse_ical(self.feed(), "u")
        self.assertEqual(event["title"], "Open Mic")
        self.assertEqual(event["starttime"], local(2026, 11, 27, 19, 0))

    def test_merged_block_is_split_per_timezone(self):
        text = split_merged_timezones(self.feed().decode())
        self.assertEqual(text.count("BEGIN:VTIMEZONE"), 2)
        self.assertEqual(text.count("END:VTIMEZONE"), 2)

    def test_well_formed_timezones_are_untouched(self):
        text = "BEGIN:VTIMEZONE\r\nTZID:America/New_York\r\nEND:VTIMEZONE\r\n"
        self.assertEqual(split_merged_timezones(text), text)


class ParseIcalTestCase(SimpleTestCase):
    def test_event_fields(self):
        [event] = parse_ical(
            ical(
                [
                    "UID:abc@venue",
                    "SUMMARY:Jazz &amp; Blues",
                    "DTSTART:20261105T200000",
                    "DESCRIPTION:<p>A great night</p>",
                    "URL:https://venue.example/e/1",
                ]
            ),
            "https://venue.example/cal.ics",
        )
        self.assertEqual(event["title"], "Jazz & Blues")
        # times without a zone are the venue's local time
        self.assertEqual(event["starttime"], local(2026, 11, 5, 20, 0))
        self.assertFalse(event["all_day"])
        self.assertEqual(event["description"], "A great night")
        self.assertEqual(event["hyperlink"], "https://venue.example/e/1")
        self.assertFalse(event["is_cancelled"])
        self.assertTrue(event["external_id"].startswith("ical:"))

    def test_utc_times_are_kept(self):
        [event] = parse_ical(
            ical(["UID:u", "SUMMARY:Show", "DTSTART:20261106T010000Z"]), "u"
        )
        self.assertEqual(event["starttime"], local(2026, 11, 5, 20, 0))

    def test_cancelled_entry(self):
        [event] = parse_ical(
            ical(["UID:c", "SUMMARY:Show", "DTSTART:20261105T200000", "STATUS:CANCELLED"]), "u"
        )
        self.assertTrue(event["is_cancelled"])

    def test_recurring_instances_get_distinct_ids(self):
        events = parse_ical(
            ical(
                ["UID:weekly", "SUMMARY:Jazz Jam", "DTSTART:20261105T200000"],
                ["UID:weekly", "SUMMARY:Jazz Jam", "DTSTART:20261112T200000"],
            ),
            "u",
        )
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0]["external_id"], events[1]["external_id"])

    def test_date_only_entry_is_all_day(self):
        [event] = parse_ical(ical(["UID:d", "SUMMARY:Fest", "DTSTART;VALUE=DATE:20261106"]), "u")
        self.assertTrue(event["all_day"])
        self.assertEqual(event["starttime"], local(2026, 11, 6))

    def test_placeholders_and_undated_entries_are_skipped(self):
        events = parse_ical(
            ical(
                ["UID:p", "SUMMARY:No Event Tonight", "DTSTART:20261105T200000"],
                ["UID:q", "SUMMARY:No date"],
            ),
            "u",
        )
        self.assertEqual(events, [])

    def test_ids_are_stable_across_parses(self):
        body = ical(["UID:abc", "SUMMARY:Show", "DTSTART:20261105T200000"])
        self.assertEqual(
            parse_ical(body, "u")[0]["external_id"], parse_ical(body, "u")[0]["external_id"]
        )


class ParseJsonLdTestCase(SimpleTestCase):
    def test_nested_event_with_performers_and_offers(self):
        script = json.dumps(
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "The Venue"},
                    {
                        "@type": "MusicEvent",
                        "name": "Samantha Fish",
                        "startDate": "2026-11-05T20:00:00-05:00",
                        "url": "https://venue.example/e/sf",
                        "description": "<p>Blues &amp; rock</p>",
                        "performer": [{"name": "Samantha Fish"}, {"name": "Sgt. Splendor"}],
                        "offers": [{"price": "$25", "url": "https://tix.example/sf"}],
                    },
                ],
            }
        )
        [event] = parse_json_ld([script], "https://venue.example/shows")
        self.assertEqual(event["title"], "Samantha Fish")
        self.assertEqual(event["artists"], "Sgt. Splendor")
        self.assertEqual(event["starttime"], local(2026, 11, 5, 20, 0))
        self.assertEqual(event["hyperlink"], "https://venue.example/e/sf")
        self.assertEqual(event["ticket_hyperlink"], "https://tix.example/sf")
        self.assertEqual(event["price_amount"], 25.0)
        self.assertEqual(event["description"], "Blues & rock")
        self.assertTrue(event["external_id"].startswith("json-ld:"))

    def test_list_nodes_type_lists_and_date_only(self):
        script = json.dumps(
            [{"@type": ["Event", "Thing"], "name": "Fest", "startDate": "2026-11-06"}]
        )
        [event] = parse_json_ld([script], "https://venue.example/")
        self.assertTrue(event["all_day"])
        # no url of its own, so the page is the link
        self.assertEqual(event["hyperlink"], "https://venue.example/")

    def test_date_only_start_is_all_day_on_that_date(self):
        script = json.dumps({"@type": "Event", "name": "Show", "startDate": "2026-11-06"})
        [event] = parse_json_ld([script], "https://venue.example/")
        self.assertTrue(event["all_day"])
        self.assertEqual(event["starttime"], local(2026, 11, 6, 0, 0))

    def test_invalid_block_is_ignored(self):
        good = json.dumps({"@type": "Event", "name": "Show", "startDate": "2026-11-05"})
        events = parse_json_ld(["{not json", good], "u")
        self.assertEqual([event["title"] for event in events], ["Show"])

    def test_cancelled_low_price_and_skipped_nodes(self):
        scripts = [
            json.dumps(
                [
                    {
                        "@type": "Event",
                        "name": "Called Off",
                        "startDate": "2026-11-05",
                        "eventStatus": "https://schema.org/EventCancelled",
                        "offers": {"@type": "AggregateOffer", "lowPrice": "1,200.50"},
                    },
                    {"@type": "Event", "name": "Undated"},
                    {"@type": "Event", "name": "Closed", "startDate": "2026-11-07"},
                ]
            )
        ]
        [event] = parse_json_ld(scripts, "u")
        self.assertTrue(event["is_cancelled"])
        self.assertEqual(event["price_amount"], 1200.5)

    def test_recurring_events_sharing_the_page_get_distinct_ids(self):
        scripts = [
            json.dumps(
                [
                    {"@type": "Event", "name": "Jam", "startDate": "2026-11-05T20:00"},
                    {"@type": "Event", "name": "Jam", "startDate": "2026-11-12T20:00"},
                ]
            )
        ]
        a, b = parse_json_ld(scripts, "u")
        self.assertNotEqual(a["external_id"], b["external_id"])


class CleaningTestCase(SimpleTestCase):
    def test_clean_text(self):
        self.assertEqual(clean_text("Rock &#038; Roll <b>Night</b>\n  live"), "Rock & Roll Night live")
        self.assertEqual(clean_text(None), "")

    def test_clean_text_strips_escaped_html(self):
        self.assertEqual(
            clean_text("&lt;h2&gt;&lt;strong&gt;Show&lt;/strong&gt;&lt;/h2&gt;&lt;p&gt;Doors &amp;amp; more&lt;/p&gt;"),
            "Show Doors & more",
        )

    def test_clean_description_truncates_on_a_word(self):
        text = clean_description("word " * 200)
        self.assertLessEqual(len(text), MAX_DESCRIPTION_LENGTH + 1)
        self.assertTrue(text.endswith("word…"))
        self.assertEqual(clean_description("short"), "short")

    def test_is_placeholder(self):
        for title in ("No Event Tonight", "no shows this week", "No Music", "CLOSED for repairs"):
            self.assertTrue(is_placeholder(title), title)
        for title in ("Closer", "Nobody's Fault", "Show: No Events Remain"):
            self.assertFalse(is_placeholder(title), title)

    def test_stable_id(self):
        self.assertEqual(stable_id("a", 1), stable_id("a", 1))
        self.assertNotEqual(stable_id("a", 1), stable_id("a", 2))
        self.assertEqual(len(stable_id("x")), 16)


class OpendateStartTimeTestCase(SimpleTestCase):
    def test_reads_the_start_time_from_the_page_data(self):
        start = opendate_start_time(OPENDATE_PAGE)
        self.assertEqual(start, local(2026, 11, 6, 22, 0))
        self.assertEqual(timezone.localtime(start).hour, 22)

    def test_no_usable_start_time(self):
        block = '<script type="application/json" class="js-react-on-rails-component">{}</script>'
        for page in [
            "<html><body>no data</body></html>",
            block.format("{not json"),
            block.replace("{}", '{"confirm": {"id": 1}}'),
            block.replace("{}", '{"confirm": {"start_time": "soon"}}'),
            block.replace("{}", '["not", "an", "object"]'),
            "",
            None,
        ]:
            with self.subTest(page=page):
                self.assertIsNone(opendate_start_time(page))


class PlaceholderMidnightTestCase(SimpleTestCase):
    OPENDATE = "https://app.opendate.io/e/roomful-of-blues-november-06-2026-1"

    def event(self, starttime, ticket=OPENDATE, all_day=False):
        return {"starttime": starttime, "ticket_hyperlink": ticket, "all_day": all_day}

    def test_placeholders(self):
        utc = datetime.timezone.utc
        for starttime in [
            datetime.datetime(2026, 11, 6, 5, 0, tzinfo=utc),  # midnight est
            datetime.datetime(2026, 10, 28, 5, 0, tzinfo=utc),  # shows as 1am edt
            local(2026, 10, 28, 0, 0),  # local midnight in summer
        ]:
            with self.subTest(starttime=starttime):
                self.assertTrue(is_placeholder_midnight(self.event(starttime)))

    def test_not_placeholders(self):
        utc = datetime.timezone.utc
        five_utc = datetime.datetime(2026, 11, 6, 5, 0, tzinfo=utc)
        for name, event in {
            "a real time": self.event(local(2026, 11, 6, 20, 0)),
            "no opendate link": self.event(five_utc, ticket="https://tix.example/1"),
            "opendate but not an event page": self.event(five_utc, ticket="https://app.opendate.io/v/venue"),
            "no ticket link": self.event(five_utc, ticket=""),
            "already all-day": self.event(local(2026, 11, 6, 0, 0), all_day=True),
        }.items():
            with self.subTest(name):
                self.assertFalse(is_placeholder_midnight(event))
