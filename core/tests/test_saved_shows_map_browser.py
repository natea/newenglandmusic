"""
the saved shows map in a real browser. the map's style and tiles come from protomaps, which
the tests block (core/tests/browser.py), so nothing is drawn: the tests read the pins the map
script made (window.siteMaps) and call its pin-click handler, the page's own code.
"""

import datetime

from core.models import Event, Venue
from core.saved_shows import COOKIE_NAME, format_saved
from core.tests.browser import BrowserTestCase
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from django.test import override_settings

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short_date(when):
    return f"{MONTHS[when.month - 1]} {when.day}"


@override_settings(PROTOMAPS_API_KEY="fake-protomaps-key")
class SavedShowsMapBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        today = beginning_of_day(get_current_new_york_datetime())
        self.day1 = today + datetime.timedelta(days=1, hours=19)
        self.day3 = today + datetime.timedelta(days=3, hours=21)
        self.paradise = Venue.objects.create(name="Paradise Rock Club", latitude=42.3519, longitude=-71.1195)
        self.higher_ground = Venue.objects.create(name="Higher Ground", latitude=44.4567, longitude=-73.2071)
        self.boston_show = Event.objects.create(title="boston show", starttime=self.day1, venue=self.paradise)
        self.vermont_show = Event.objects.create(title="vermont show", starttime=self.day3, venue=self.higher_ground)

    def open_saved(self, *events):
        context = self.browser.new_context()
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        context.add_cookies([{"name": COOKIE_NAME, "value": format_saved([e.pk for e in events]), "url": self.live_server_url}])
        return self.open_page("/saved", context=context)[1]

    def open_map(self, page):
        page.click('a[data-map="all"]')
        page.wait_for_function("() => window.siteMaps && window.siteMaps.all")

    def pins(self, page):
        return page.evaluate(
            "() => window.siteMaps.all.features.map(f => ({venues: f.properties.venueIds, times: f.properties.startTime, label: f.properties.label}))"
        )

    def test_not_loaded_until_opened(self):
        page = self.open_saved(self.boston_show)
        self.assertFalse(page.evaluate("() => !!(window.siteMaps && window.siteMaps.all)"))
        self.assertEqual(page.locator("#map-all canvas").count(), 0)
        self.assertFalse([url for url in self.blocked if "protomaps" in url])
        self.assertFalse(page.locator("#map-all").is_visible())

    def test_map_of_saved_shows_over_several_days(self):
        page = self.open_saved(self.boston_show, self.vermont_show)
        self.open_map(page)
        self.assertTrue(page.locator("#map-all").is_visible())
        self.assertEqual(page.locator('a[data-map="all"]').inner_text(), "HIDE MAP")
        pins = self.pins(page)
        self.assertEqual(len(pins), 2)
        self.assertEqual(
            sorted(pin["times"] for pin in pins),
            sorted([f"{short_date(self.day1)} 7:00pm", f"{short_date(self.day3)} 9:00pm"]),
        )
        # fitted to both pins: the map's bounds hold both venues
        self.assertTrue(
            page.evaluate(
                """() => {
                    const bounds = window.siteMaps.all.map.getBounds();
                    return bounds.contains([-71.1195, 42.3519]) && bounds.contains([-73.2071, 44.4567]);
                }"""
            )
        )

    def test_shows_at_one_venue_share_a_pin(self):
        later = Event.objects.create(title="later boston show", starttime=self.day3, venue=self.paradise)
        page = self.open_saved(self.boston_show, later)
        self.open_map(page)
        pins = self.pins(page)
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0]["times"], f"{short_date(self.day1)} 7:00pm, {short_date(self.day3)} 9:00pm")

    def test_next_door_venues_share_a_pin(self):
        # the 9:30 Club and The Atlantis, 28 metres apart
        nine_thirty = Venue.objects.create(name="9:30 Club", latitude=38.917948, longitude=-77.0237227)
        atlantis = Venue.objects.create(name="The Atlantis", latitude=38.9181819, longitude=-77.023636)
        dana = Event.objects.create(title="Dana and Alden", starttime=self.day1, venue=atlantis)
        rooks = Event.objects.create(title="Giant Rooks", starttime=self.day3, venue=nine_thirty)
        page = self.open_saved(dana, rooks)
        self.open_map(page)
        pins = self.pins(page)
        self.assertEqual(len(pins), 1)
        self.assertEqual(sorted(pins[0]["venues"].split(",")), sorted([str(atlantis.pk), str(nine_thirty.pk)]))
        self.assertEqual(
            pins[0]["label"].split("\n"),
            [f"{short_date(self.day1)} 7:00pm Dana and Alden", f"{short_date(self.day3)} 9:00pm Giant Rooks"],
        )
        page.evaluate("() => window.siteMaps.all.showPin(window.siteMaps.all.features[0])")
        self.assertEqual(page.locator("#map-all-info div.event").count(), 2)

    def test_venues_a_street_apart_keep_their_own_pins(self):
        # about 100 metres north of Paradise Rock Club
        neighbour = Venue.objects.create(name="Up the street", latitude=42.3528, longitude=-71.1195)
        nearby = Event.objects.create(title="nearby show", starttime=self.day3, venue=neighbour)
        page = self.open_saved(self.boston_show, nearby)
        self.open_map(page)
        self.assertEqual(len(self.pins(page)), 2)

    def test_clicking_a_pin_lists_its_shows(self):
        later = Event.objects.create(title="later boston show", starttime=self.day3, venue=self.paradise)
        page = self.open_saved(self.boston_show, later, self.vermont_show)
        self.open_map(page)
        page.evaluate(
            f"""() => {{
                const pin = window.siteMaps.all.features.find(f => f.properties.venueIds.split(',').includes('{self.paradise.pk}'));
                window.siteMaps.all.showPin(pin);
            }}"""
        )
        info = page.locator("#map-all-info")
        self.assertTrue(info.is_visible())
        self.assertEqual(info.locator("div.event").count(), 2)
        self.assertIn("boston show", info.inner_text())
        self.assertNotIn("vermont show", info.inner_text())
        # with their icon rows, and their days above their times
        self.assertEqual(info.locator("div.event-actions").count(), 2)
        days = info.locator(".event-time .event-date").all_inner_texts()
        self.assertEqual(days, [f"{self.day1:%a}\n{short_date(self.day1)}", f"{self.day3:%a}\n{short_date(self.day3)}"])
        # the day, the date and the time on lines of their own
        self.assertEqual(
            [line.strip() for line in info.locator(".event-time").first.inner_text().split("\n") if line.strip()],
            [f"{self.day1:%a}", short_date(self.day1), "7:00pm"],
        )
        # and the text starts where the listing's does: the time column keeps its width
        widths = page.evaluate(
            """() => [document.querySelector('#map-all-info .event-time').offsetWidth,
                      document.querySelector('article .event-time').offsetWidth]"""
        )
        self.assertEqual(widths[0], widths[1])

    def test_shows_that_cant_be_mapped(self):
        nowhere = Venue.objects.create(name="Nowhere")
        unplaced = Event.objects.create(title="unplaced show", starttime=self.day1, venue=nowhere)
        no_venue = Event.objects.create(title="basement show", starttime=self.day1, venue_override="a basement")
        cancelled = Event.objects.create(
            title="cancelled show", starttime=self.day1, venue=self.higher_ground, is_cancelled=True
        )
        page = self.open_saved(self.boston_show, unplaced, no_venue, cancelled)
        self.open_map(page)
        pins = self.pins(page)
        self.assertEqual([pin["venues"] for pin in pins], [str(self.paradise.pk)])
        self.assertEqual(pins[0]["times"], f"{short_date(self.day1)} 7:00pm")
        for title in ("unplaced show", "basement show", "cancelled show"):
            self.assertIn(title, page.locator("article").inner_text())

    def test_hide_map(self):
        page = self.open_saved(self.boston_show)
        self.open_map(page)
        page.click('a[data-map="all"]')
        self.assertFalse(page.locator("#map-all").is_visible())
        self.assertEqual(page.locator('a[data-map="all"]').inner_text(), "SHOW MAP")

    def test_day_maps_unchanged(self):
        _, page = self.open_page("/")
        key = f"{self.day1:%m%d%y}"
        # the homepage opens its first day's map by itself, which may be today's: open this one
        page.wait_for_function("() => window.siteMaps && Object.keys(window.siteMaps).length")
        if not page.evaluate(f"() => !!window.siteMaps['{key}']"):
            page.click(f'a[data-date="{key}"]')
        page.wait_for_function(f"() => window.siteMaps && window.siteMaps['{key}']")
        times = page.evaluate(f"() => window.siteMaps['{key}'].features.map(f => f.properties.startTime)")
        self.assertEqual(times, ["7:00pm"])
        # and a day map's panel shows no dates: its shows are all on that day
        page.evaluate(f"() => window.siteMaps['{key}'].showPin(window.siteMaps['{key}'].features[0])")
        self.assertEqual(page.locator(f"#map-{key}-info .event-date").count(), 0)
        self.assertEqual(page.locator(f"#map-{key}-info div.event").count(), 1)
        self.assertFalse(page.evaluate("() => !!window.siteMaps.all"))
