"""
the site's named posthog events in a real browser (add-posthog-analytics). posthog itself never
loads: its host is blocked like every other outside request (core/tests/browser.py), and a stub
put in the page before its scripts run (add_init_script) stands in for it, recording each
capture in sessionStorage, so an event sent just before a page navigates is still counted.
the stub drops captures once opted out, as posthog does.
"""

import datetime
import json
from unittest import mock

from core.models import Band, Event, SpotifyArtistLink
from core.tests.browser import BrowserTestCase
from core.tests.new_england_fixture import new_england_venue
from core.tests.spotify_fixture import CREDENTIALS
from core.tests.test_discover_browser import DeckBrowserTestCase
from django.test import override_settings
from django.utils import timezone

STUB = """
(() => {
  const read = () => JSON.parse(sessionStorage.getItem("captures") || "[]");
  window.posthog = {
    __SV: 1,
    __loaded: true,
    init(token, options) {
      sessionStorage.setItem("init", JSON.stringify(options));
      if (options.loaded) setTimeout(() => options.loaded(this), 0);
    },
    capture(name, properties, options) {
      if (localStorage.getItem("opted_out") === "1") return;
      const all = read();
      all.push({ name, properties: properties || {}, options: options || null });
      sessionStorage.setItem("captures", JSON.stringify(all));
    },
    opt_out_capturing() { localStorage.setItem("opted_out", "1"); },
    opt_in_capturing() { localStorage.removeItem("opted_out"); },
    has_opted_out_capturing() { return localStorage.getItem("opted_out") === "1"; },
  };
})();
"""

ON = {"POSTHOG_PROJECT_TOKEN": "phc_test_token", "POSTHOG_HOST": "https://us.i.posthog.com"}


class StubbedPostHog:
    """a browser context with the posthog stub, and what it captured"""

    def stubbed_page(self, path):
        context = self.browser.new_context(viewport={"width": 1100, "height": 900})
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        context.add_init_script(STUB)
        self.context = context
        _, page = self.open_page(path, context=context)
        return page

    def captures(self, page):
        return page.evaluate("() => JSON.parse(sessionStorage.getItem('captures') || '[]')")

    def named(self, page, name):
        return [c for c in self.captures(page) if c["name"] == name]


@override_settings(**ON)
class ListingEventsTestCase(StubbedPostHog, BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict("os.environ", CREDENTIALS))
        self.belly = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        now = timezone.now()
        SpotifyArtistLink.objects.create(
            name_key="belly", status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id="fakeBelly",
            checked_at=now, last_seen_at=now,
        )
        self.show = Event.objects.create(
            venue=new_england_venue(), artists="Belly", starttime=now + datetime.timedelta(days=1),
            ticket_hyperlink="https://tickets.example/belly",
        )

    def test_initialised_for_privacy(self):
        page = self.stubbed_page("/")
        options = json.loads(page.evaluate("() => sessionStorage.getItem('init')"))
        self.assertEqual(options["api_host"], "https://us.i.posthog.com")
        self.assertIs(options["disable_session_recording"], True)
        self.assertEqual(options["person_profiles"], "identified_only")

    def test_a_search(self):
        page = self.stubbed_page("/bands")
        box = page.locator(".site-search input[name=s]")
        box.fill("belly")
        with page.expect_navigation():
            box.press("Enter")
        searches = self.named(page, "search")
        self.assertEqual([s["properties"] for s in searches], [{"query": "belly"}])
        self.assertEqual(searches[0]["options"], {"transport": "sendBeacon", "send_instantly": True})

    def test_a_suggestion_chosen(self):
        page = self.stubbed_page("/bands")
        box = page.locator(".site-search input[name=s]")
        box.press_sequentially("bel")
        page.wait_for_selector(".autocomplete__option")
        box.press("ArrowDown")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        self.assertTrue(page.url.endswith("/bands/belly"))
        chosen = self.named(page, "search_suggestion_chosen")
        self.assertEqual([c["properties"] for c in chosen], [{"kind": "band", "query": "bel"}])

    def test_a_show_saved(self):
        page = self.stubbed_page("/")
        button = page.locator(f".save[data-event-id='{self.show.pk}']").first
        button.click()
        button.click()
        self.assertEqual(
            [(c["name"], c["properties"]) for c in self.captures(page) if c["name"].startswith("show_")],
            [("show_saved", {"event_id": str(self.show.pk), "show": "Belly"}),
             ("show_unsaved", {"event_id": str(self.show.pk), "show": "Belly"})],
        )

    def test_a_play_button(self):
        page = self.stubbed_page("/")
        page.locator("a.spotify-play").first.click()
        self.assertEqual([c["properties"] for c in self.named(page, "preview_played")], [{"service": "spotify"}])

    def test_a_ticket_link(self):
        page = self.stubbed_page("/")
        page.locator(f"#event-{self.show.pk} a.ticket").click()
        page.wait_for_function("() => (sessionStorage.getItem('captures') || '').includes('ticket_link_opened')")
        opened = self.named(page, "ticket_link_opened")
        self.assertEqual([o["properties"] for o in opened], [{"event_id": str(self.show.pk), "show": "Belly"}])
        self.assertEqual(opened[0]["options"], {"transport": "sendBeacon", "send_instantly": True})

    def test_a_show_added_to_a_calendar(self):
        page = self.stubbed_page("/")
        with page.expect_download():
            page.locator(f"#event-{self.show.pk} a.ical").click()
        self.assertEqual(
            [c["properties"] for c in self.named(page, "show_added_to_calendar")],
            [{"how": "ics", "event_id": str(self.show.pk), "show": "Belly"}],
        )

    def test_a_search_that_finds_nothing(self):
        page = self.stubbed_page("/?s=zzzz")
        page.wait_for_function("() => (sessionStorage.getItem('captures') || '').includes('search_results_viewed')")
        self.assertEqual(
            [c["properties"] for c in self.named(page, "search_results_viewed")],
            [{"query": "zzzz", "acts": 0, "venues": 0, "upcoming": 0, "past": 0, "pages": 0, "total": 0}],
        )

    def test_a_searchs_counts(self):
        venue = self.show.venue
        Event.objects.create(venue=venue, artists="Belly", starttime=timezone.now() + datetime.timedelta(days=5))
        Event.objects.create(venue=venue, artists="Belly", starttime=timezone.now() - datetime.timedelta(days=5))
        page = self.stubbed_page("/?s=belly")
        page.wait_for_function("() => (sessionStorage.getItem('captures') || '').includes('search_results_viewed')")
        viewed = self.named(page, "search_results_viewed")[0]["properties"]
        self.assertEqual((viewed["acts"], viewed["upcoming"], viewed["past"]), (1, 2, 1))
        self.assertEqual(viewed["total"], viewed["acts"] + viewed["venues"] + viewed["upcoming"] + viewed["past"] + viewed["pages"])

    def test_an_act_page(self):
        from core.models import EventPerformer

        EventPerformer.objects.create(event=self.show, band=self.belly, order=0)
        page = self.stubbed_page(self.belly.get_absolute_url())
        page.wait_for_function("() => (sessionStorage.getItem('captures') || '').includes('act_page_viewed')")
        self.assertEqual(
            [c["properties"] for c in self.named(page, "act_page_viewed")],
            [{"name": "Belly", "kind": "band", "has_upcoming_show": True}],
        )

    def test_a_submissions_email_stays_out(self):
        page = self.stubbed_page("/submit-event")
        page.fill("input[name=user_submission_email]", "someone.private@example.org")
        page.click("input[type=submit], button[type=submit]")
        page.wait_for_load_state()
        sent = json.dumps(self.captures(page))
        self.assertNotIn("someone.private", sent)

    def test_nothing_from_the_location(self):
        page = self.stubbed_page("/")
        self.context.add_cookies([{"name": "near", "value": "42.3601|-71.0589|Boston, MA", "url": self.live_server_url}])
        page.goto(self.live_server_url + "/")
        page.locator(f".save[data-event-id='{self.show.pk}']").first.click()
        page.locator("a.spotify-play").first.click()
        sent = json.dumps(self.captures(page))
        for value in ("42.36", "-71.05", "mi away"):
            self.assertNotIn(value, sent)


@override_settings(**ON)
class TurningItOffTestCase(StubbedPostHog, BrowserTestCase):
    def test_turning_it_off(self):
        page = self.stubbed_page("/privacy")
        toggle = page.locator("#analytics-toggle")
        toggle.wait_for(state="visible")
        self.assertEqual(toggle.inner_text(), "Turn off analytics in this browser")
        toggle.click()
        self.assertEqual(toggle.inner_text(), "Turn analytics back on in this browser")
        box = page.locator(".site-search input[name=s]")
        box.fill("belly")
        with page.expect_navigation():
            box.press("Enter")
        self.assertEqual(self.named(page, "search"), [])
        # and back on: searches are sent again
        page.goto(self.live_server_url + "/privacy")
        page.locator("#analytics-toggle").click()
        box = page.locator(".site-search input[name=s]")
        box.fill("belly")
        with page.expect_navigation():
            box.press("Enter")
        self.assertEqual(len(self.named(page, "search")), 1)


@override_settings(**ON)
class DeckEventsTestCase(StubbedPostHog, DeckBrowserTestCase):
    def open_stubbed_deck(self):
        self.make_deck()
        page = self.stubbed_page("/discover")
        page.click(".deck-start")
        return page

    def test_a_pass_and_shows_saved(self):
        page = self.open_stubbed_deck()
        self.skip_to_belly(page)
        page.click(".deck-add")
        page.wait_for_selector(".picker")
        page.locator(".picker-row .picker-text").nth(0).click()
        page.locator(".picker-row .picker-text").nth(1).click()
        page.click(".picker-save")
        self.assertEqual(len(self.named(page, "deck_act_passed")), 1)
        self.assertEqual([c["properties"] for c in self.named(page, "deck_shows_saved")], [{"count": 2}])
