from core.event_sources import (
    CSV_COLUMNS,
    event_source_csv_row,
    event_source_row,
    save_event_source,
)
from core.models import Event, Venue, VenueEventSource
from django.forms.models import model_to_dict
from django.test import TestCase
from django.utils import timezone


def result(**values):
    row = {
        "sheet_id": "V0001",
        "name": "Venue V0001",
        "state": "VT",
        "city_town": "Burlington",
        "url": "https://v0001.example/",
        "events_page": "https://v0001.example/calendar",
        "best_source": "ical",
        "json_ld_events": 2,
        "ical_url": "https://v0001.example/cal.ics",
        "ical_events": 12,
        "platforms": "dice;eventbrite",
        "js_heavy": "yes",
        "error": "events page timed out",
    }
    row.update(values)
    return row


class EventSourcesTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(
            sheet_id="V0001", name="Venue V0001", state="VT", city_town="Burlington"
        )

    def test_round_trip_to_csv(self):
        source = save_event_source(self.venue, result())
        row = event_source_csv_row(source)
        self.assertEqual(list(row), CSV_COLUMNS)
        self.assertEqual(
            {k: str(v) for k, v in row.items()},
            {k: str(v) for k, v in result().items()},
        )
        self.assertEqual(source.platforms, ["dice", "eventbrite"])
        self.assertTrue(source.js_heavy)

    def test_csv_strings_and_blanks(self):
        # a row read back from a csv has strings, and blanks for missing counts
        source = save_event_source(
            self.venue,
            result(json_ld_events="5", ical_events="", platforms="", js_heavy=""),
        )
        self.assertEqual(source.json_ld_events, 5)
        self.assertIsNone(source.ical_events)
        self.assertEqual(source.platforms, [])
        self.assertFalse(source.js_heavy)
        self.assertEqual(event_source_csv_row(source)["ical_events"], "")

    def test_failed_check_result(self):
        # check_venue's catch-all result has only some of the keys
        source = save_event_source(
            self.venue,
            {
                "sheet_id": "V0001",
                "url": "https://v0001.example/",
                "best_source": "check-failed",
                "error": "boom",
            },
        )
        self.assertEqual(source.best_source, "check-failed")
        self.assertEqual(source.json_ld_events, 0)

    def test_reader_row(self):
        row = event_source_row(save_event_source(self.venue, result()))
        self.assertEqual(row["sheet_id"], "V0001")
        self.assertEqual(row["best_source"], "ical")
        self.assertEqual(row["platforms"], ["dice", "eventbrite"])

    def test_saving_twice_keeps_one_row(self):
        save_event_source(self.venue, result())
        save_event_source(
            self.venue, result(best_source="ticketing", ical_url="", ical_events="")
        )
        self.assertEqual(VenueEventSource.objects.filter(venue=self.venue).count(), 1)
        self.venue.event_source.refresh_from_db()
        self.assertEqual(self.venue.event_source.best_source, "ticketing")
        self.assertEqual(self.venue.event_source.ical_url, "")

    def test_venue_and_its_events_untouched(self):
        event = Event.objects.create(
            title="a show", venue=self.venue, starttime=timezone.now()
        )
        Event.all_objects.filter(pk=event.pk).update(
            baked_html_template="<p>stored</p>"
        )
        before = model_to_dict(Venue.objects.get(pk=self.venue.pk))
        save_event_source(self.venue, result())
        self.assertEqual(model_to_dict(Venue.objects.get(pk=self.venue.pk)), before)
        self.assertEqual(
            Event.all_objects.get(pk=event.pk).baked_html_template, "<p>stored</p>"
        )
