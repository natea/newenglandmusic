import re
from datetime import timedelta
from unittest import mock

from core.models import Event, SpotifyArtistLink, Venue
from core.saved_shows import COOKIE_NAME, MAX_SAVED, format_saved, parse_saved
from core.tests.spotify_fixture import CREDENTIALS
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from django.test import TestCase
from django.utils import timezone

ROW = re.compile(r'<div class="event-actions">(.*?)</div>', re.S)


def row_of(html, event):
    """the icon row inside the event's element on a page"""
    start = html.index(f'id="event-{event.pk}"')
    return ROW.search(html, start).group(1)


class IconRowTestCase(TestCase):
    def setUp(self):
        self.tomorrow = beginning_of_day(get_current_new_york_datetime()) + timedelta(days=1, hours=20)
        self.paradise = Venue.objects.create(
            name="Paradise Rock Club", latitude=42.3519, longitude=-71.1195, city_town="Boston", state="MA"
        )
        self.event = Event.objects.create(title="a show", starttime=self.tomorrow, venue=self.paradise)

    def homepage(self):
        return self.client.get("/").content.decode()

    def test_icons_with_names_in_order(self):
        row = row_of(self.homepage(), self.event)
        names = re.findall(r'\stitle="([^"]+)"', row)
        self.assertEqual(
            names,
            ["Download to your calendar (.ics)", "Add to Google Calendar", "Map: Paradise Rock Club", "Share", "Save show"],
        )
        # no icon has visible text, so each title is also its accessible name
        self.assertNotRegex(re.sub(r"<[^>]+>", "", row).strip(), r"\w")
        self.assertIn(f'href="/event/{self.event.pk}/ics"', row)
        self.assertIn(f'href="/event/{self.event.pk}/gcal"', row)
        self.assertIn(f'href="/event/{self.event.pk}"', row)
        self.assertIn('target="_blank" rel="noopener"', row)

    def test_no_map_without_a_location(self):
        nowhere = Venue.objects.create(name="Nowhere")
        unplaced = Event.objects.create(title="unplaced", starttime=self.tomorrow, venue=nowhere)
        overridden = Event.objects.create(
            title="overridden", starttime=self.tomorrow, venue=self.paradise, venue_override="a basement"
        )
        html = self.homepage()
        for event in (unplaced, overridden):
            self.assertNotIn('class="map"', row_of(html, event))
            self.assertIn('class="share"', row_of(html, event))

    def test_own_row_before_the_play_buttons(self):
        with mock.patch.dict("os.environ", CREDENTIALS):
            now = timezone.now()
            SpotifyArtistLink.objects.create(
                name_key="a show", status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id="fakeShow",
                checked_at=now, last_seen_at=now,
            )
            self.event.save()
            html = self.homepage()
        event = html[html.index(f'id="event-{self.event.pk}"'):]
        text_ends = event.index('<div class="event-ticket">')
        self.assertLess(text_ends, event.index('<div class="event-actions">'))
        self.assertLess(event.index('<div class="event-actions">'), event.index('<div class="artist-previews">'))
        # none of the links, nor any "+", left in the text
        text = event[: text_ends]
        self.assertNotIn('class="ical"', text)
        self.assertNotRegex(re.sub(r"<[^>]+>", " ", text), r"\s\+\s")

    def test_search_results(self):
        html = self.client.get("/?s=show").content.decode()
        self.assertIn('class="save"', row_of(html, self.event))

    def test_not_in_the_stored_html(self):
        stored = Event.objects.get(pk=self.event.pk).baked_html_template
        self.assertIn("<!--event-actions-->", stored)
        for link in ('class="ical"', 'class="gcal"', 'class="map"', 'class="share"', 'class="save'):
            self.assertNotIn(link, stored)

    def test_icons_defined_once(self):
        Event.objects.create(title="another show", starttime=self.tomorrow, venue=self.paradise)
        html = self.homepage()
        for name in ("ical", "gcal", "map", "share", "save"):
            self.assertEqual(html.count(f'<symbol id="icon-{name}"'), 1, name)
            # one reference per event's row: both events are at a located venue
            self.assertEqual(html.count(f'<use href="#icon-{name}">'), 2, name)

    def test_saved_state_shown_on_load(self):
        other = Event.objects.create(title="other show", starttime=self.tomorrow, venue=self.paradise)
        self.client.cookies[COOKIE_NAME] = format_saved([self.event.pk])
        html = self.homepage()
        saved, unsaved = row_of(html, self.event), row_of(html, other)
        self.assertIn('class="save is-saved"', saved)
        self.assertIn('aria-pressed="true" title="Saved (click to remove)"', saved)
        self.assertIn('class="save"', unsaved)
        self.assertIn('aria-pressed="false" title="Save show"', unsaved)

    def test_back_to_the_same_page_and_event(self):
        row = row_of(self.client.get("/?state=nowhere").content.decode(), self.event)
        self.assertIn(f'name="next" value="/?state=nowhere#event-{self.event.pk}"', row)


class ToggleTestCase(TestCase):
    def setUp(self):
        self.show = Event.objects.create(title="a show", starttime=timezone.now() + timedelta(days=2))

    def toggle(self, event_id, next_url="/", saved=None):
        if saved is not None:
            self.client.cookies[COOKIE_NAME] = format_saved(saved)
        return self.client.post(f"/saved/toggle/{event_id}", {"next": next_url})

    def test_saves_and_returns_to_the_event(self):
        response = self.toggle(self.show.pk, next_url=f"/?state=vermont#event-{self.show.pk}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/?state=vermont#event-{self.show.pk}")
        self.assertEqual(parse_saved(response.cookies[COOKIE_NAME].value), [self.show.pk])
        self.assertEqual(response.cookies[COOKIE_NAME]["samesite"], "Lax")

    def test_unsaves(self):
        response = self.toggle(self.show.pk, saved=[self.show.pk, 7])
        self.assertEqual(parse_saved(response.cookies[COOKIE_NAME].value), [7])

    def test_unsaving_the_last_show_deletes_the_cookie(self):
        response = self.toggle(self.show.pk, saved=[self.show.pk])
        self.assertEqual((response.cookies[COOKIE_NAME].value, response.cookies[COOKIE_NAME]["max-age"]), ("", 0))

    def test_newest_first_and_the_limit(self):
        full = list(range(100000, 100000 + MAX_SAVED))
        response = self.toggle(self.show.pk, saved=full)
        saved = parse_saved(response.cookies[COOKIE_NAME].value)
        self.assertEqual((len(saved), saved[0]), (MAX_SAVED, self.show.pk))
        self.assertNotIn(full[-1], saved)

    def test_unknown_event_not_saved(self):
        response = self.toggle(999999, saved=[self.show.pk])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(parse_saved(response.cookies[COOKIE_NAME].value), [self.show.pk])

    def test_other_sites_refused(self):
        for next_url in ("https://evil.example/", "//evil.example/x", "javascript:alert(1)"):
            response = self.toggle(self.show.pk, next_url=next_url)
            self.assertEqual(response["Location"], "/", next_url)

    def test_get_refused(self):
        response = self.client.get(f"/saved/toggle/{self.show.pk}")
        self.assertEqual(response.status_code, 405)
        self.assertNotIn(COOKIE_NAME, response.cookies)
