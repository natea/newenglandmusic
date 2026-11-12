"""
the discovery deck in a real browser (playwright's headless chromium), for what only
javascript does. every request that isn't to the test server is aborted and remembered in
self.blocked, so nothing really loads from any service.

see core/tests/browser.py.
"""

import os
from unittest import mock

from core.models import Band
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.browser import BrowserTestCase
from core.tests.discover_fixture import apple, days, show, spotify, venue, youtube
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_ON
from core.tests.youtube_fixture import SWITCHED_ON as YOUTUBE_ON


class DiscoverBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}))
        self.lupo = venue()

    def make_act(self, name, services=("youtube", "apple", "spotify"), shows=1):
        band = Band.objects.create(name=name, city_town="Providence", state="RI")
        key = name.lower()
        for service in services:
            {"youtube": youtube, "apple": apple, "spotify": spotify}[service](key)
        events = [show(band, days(3 + n), self.lupo) for n in range(shows)]
        return band, events

    def requests_to(self, *hosts):
        return [url for url in self.blocked if any(host in url for host in hosts)]


class PlayersAreNotRequestedUntilClickedTestCase(DiscoverBrowserTestCase):
    def test_the_page_itself_requests_nothing_from_apple_music_or_youtube(self):
        # the page's own markup has buttons only: a player is made by the script, for the
        # top card or on a click (see the deck tests)
        self.make_act("Belly", services=("youtube", "apple"))
        _, page = self.open_page("/discover", javascript=False)
        self.assertEqual(page.locator("a.youtube-play").count(), 1)
        self.assertEqual(page.locator("a.apple-play").count(), 1)
        self.assertEqual(page.locator("iframe").count(), 0)
        self.assertEqual(self.requests_to("apple.com", "youtube"), [])


def by_name(cards):
    cards.sort(key=lambda card: card.act.name)


class DeckBrowserTestCase(DiscoverBrowserTestCase):
    """a deck in a fixed order: Anjimile, Belly, Cheap Trick"""

    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch("core.views.discover.random.shuffle", by_name))

    def make_deck(self, services=("youtube", "apple", "spotify")):
        for name in ("Anjimile", "Belly", "Cheap Trick"):
            if not Band.objects.filter(name=name).exists():
                self.make_act(name, services=services if name == "Belly" else (), shows=3 if name == "Belly" else 1)

    def open_deck(self, services=("youtube", "apple", "spotify"), cookie=None, width=None, reduced_motion=False):
        self.make_deck(services)
        context = self.browser.new_context(
            viewport={"width": width or 1000, "height": 900},
            reduced_motion="reduce" if reduced_motion else "no-preference",
        )
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        if cookie:
            context.add_cookies([{"name": "saved_shows", "value": cookie, "url": self.live_server_url}])
        _, page = self.open_page("/discover", context=context)
        self.context = context
        return page

    def shown(self, page):
        return page.locator(".discover-card:not([hidden])").get_attribute("data-act")

    def cookie(self):
        found = [c["value"] for c in self.context.cookies() if c["name"] == "saved_shows"]
        return found[0].replace("%2C", ",") if found else ""

    def skip_to_belly(self, page):
        page.click(".deck-skip")
        page.wait_for_function("() => document.querySelector('.discover-card:not([hidden])').dataset.act === 'Belly'")

    def belly_events(self):
        from core.models import Event

        return list(Event.objects.filter(performers__band__name="Belly").order_by("starttime").values_list("pk", flat=True))


class SwipingTestCase(DeckBrowserTestCase):
    def swipe(self, page, dx, selector=".discover-name"):
        box = page.locator(f".discover-card:not([hidden]) {selector}").bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + dx / 2, y, steps=4)
        page.mouse.move(x + dx, y, steps=4)
        page.mouse.up()

    def wait_for(self, page, act):
        page.wait_for_function("name => document.querySelector('.discover-card:not([hidden])')?.dataset.act === name", arg=act)

    def test_one_card_at_a_time(self):
        page = self.open_deck()
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertEqual(page.locator(".discover-card:not([hidden])").count(), 1)

    def test_skip_by_swipe(self):
        page = self.open_deck()
        self.swipe(page, -200)
        self.wait_for(page, "Belly")
        self.assertEqual(self.cookie(), "")
        self.assertEqual(page.locator(".picker").count(), 0)

    def test_skip_by_button_and_key(self):
        page = self.open_deck()
        page.click(".deck-skip")
        self.wait_for(page, "Belly")
        page.keyboard.press("ArrowLeft")
        self.wait_for(page, "Cheap Trick")
        self.assertEqual(self.cookie(), "")

    def test_a_short_drag_snaps_back(self):
        page = self.open_deck()
        self.swipe(page, -30)
        page.wait_for_timeout(300)
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertEqual(page.locator(".picker").count(), 0)

    def test_the_end_of_the_deck(self):
        page = self.open_deck()
        for _ in range(3):
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(250)
        self.assertTrue(page.locator(".deck-end").is_visible())
        self.assertEqual(page.locator(".deck-saved").get_attribute("href"), "/saved")
        self.assertEqual(page.locator(".discover-card:not([hidden])").count(), 0)
        page.click(".deck-again")
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertFalse(page.locator(".deck-end").is_visible())

    def test_swiping_right_opens_the_picker_after_the_action_only(self):
        page = self.open_deck()
        self.assertEqual(page.locator(".picker").count(), 0)
        self.swipe(page, 200)
        page.wait_for_selector(".picker")
        self.assertEqual(self.shown(page), "Anjimile")


class PickerTestCase(DeckBrowserTestCase):
    def open_picker(self, **options):
        page = self.open_deck(**options)
        self.skip_to_belly(page)
        page.click(".deck-add")
        page.wait_for_selector(".picker")
        return page

    def rows(self, page):
        return page.locator(".picker-row")

    def test_the_picker_lists_the_acts_shows_soonest_first_and_none_ticked(self):
        page = self.open_picker()
        self.assertEqual(self.rows(page).count(), 3)
        texts = self.rows(page).all_inner_texts()
        for text in texts:
            self.assertIn("Lupo's, Providence, RI", text)
            self.assertRegex(text, r"[A-Z][a-z]{2}, [A-Z][a-z]{2} \d+ · \d+:\d\d [ap]\.m\.")
        self.assertEqual(page.locator(".picker-row input:checked").count(), 0)
        self.assertEqual(page.inner_text(".picker-save"), "Save 0 shows")
        # soonest first: the values are the events' ids in order
        values = [int(v) for v in page.eval_on_selector_all(".picker-row input", "boxes => boxes.map(b => b.value)")]
        self.assertEqual(values, self.belly_events())

    def test_tapping_the_row_ticks_it_and_ticking_saves_nothing(self):
        page = self.open_picker()
        # the text, away from the checkbox
        self.rows(page).nth(0).locator(".picker-text").click()
        self.assertEqual(page.locator(".picker-row input:checked").count(), 1)
        self.assertEqual(page.inner_text(".picker-save"), "Save 1 show")
        self.assertEqual(self.cookie(), "")
        self.rows(page).nth(0).locator(".picker-text").click()
        self.assertEqual(page.locator(".picker-row input:checked").count(), 0)

    def test_closing_changes_nothing_and_shows_the_same_card(self):
        page = self.open_picker()
        self.rows(page).nth(0).click()
        page.click(".picker-close")
        self.assertEqual(page.locator(".picker").count(), 0)
        self.assertEqual(self.shown(page), "Belly")
        self.assertEqual(self.cookie(), "")

    def test_escape_closes_the_picker(self):
        page = self.open_picker()
        page.keyboard.press("Escape")
        self.assertEqual(page.locator(".picker").count(), 0)
        self.assertEqual(self.shown(page), "Belly")

    def test_saving_with_nothing_ticked_keeps_the_picker_open(self):
        page = self.open_picker()
        page.click(".picker-save")
        self.assertEqual(page.locator(".picker").count(), 1)
        self.assertEqual(self.cookie(), "")

    def test_saving_two_shows(self):
        page = self.open_picker()
        first, _, third = self.belly_events()
        self.rows(page).nth(0).click()
        self.rows(page).nth(2).click()
        self.assertEqual(page.inner_text(".picker-save"), "Save 2 shows")
        page.click(".picker-save")
        self.assertEqual(sorted(int(i) for i in self.cookie().split(",")), sorted([first, third]))
        self.assertEqual(page.locator(".picker").count(), 0)
        self.assertEqual(self.shown(page), "Cheap Trick")
        self.assertEqual(page.inner_text("a.saved-count"), "Saved shows (2)")

    def test_the_saved_shows_page_lists_them(self):
        page = self.open_picker()
        self.rows(page).nth(1).click()
        page.click(".picker-save")
        saved = self.belly_events()[1]
        _, saved_page = self.open_page("/saved", context=self.context)
        self.assertEqual(saved_page.locator(f"#event-{saved}").count(), 1)

    def test_other_saved_shows_survive_a_confirm(self):
        from core.models import Event

        self.make_deck()
        other = Event.objects.filter(performers__band__name="Anjimile").first()
        page = self.open_deck(cookie=str(other.pk))
        self.skip_to_belly(page)
        page.click(".deck-add")
        self.rows(page).nth(0).click()
        page.click(".picker-save")
        ids = [int(i) for i in self.cookie().split(",")]
        self.assertEqual(ids, [self.belly_events()[0], other.pk])

    def test_a_saved_show_is_ticked_and_marked_and_unticking_removes_it(self):
        self.make_deck()
        events = self.belly_events()
        page = self.open_deck(cookie=str(events[1]))
        self.skip_to_belly(page)
        page.click(".deck-add")
        self.assertEqual(page.locator(".picker-row input:checked").count(), 1)
        self.assertTrue(self.rows(page).nth(1).locator("input").is_checked())
        self.assertIn("Saved", self.rows(page).nth(1).inner_text())
        # confirming with the ticks as they were changes nothing, and the picker stays
        page.click(".picker-save")
        self.assertEqual(page.locator(".picker").count(), 1)
        self.assertEqual(self.cookie(), str(events[1]))
        # unticking the last saved show removes it, and the next card is shown
        self.rows(page).nth(1).click()
        page.click(".picker-save")
        self.assertEqual(self.cookie(), "")
        self.assertEqual(self.shown(page), "Cheap Trick")

    def test_adding_on_the_last_card_ends_the_deck(self):
        page = self.open_deck()
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(250)
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(250)
        page.keyboard.press("ArrowRight")
        page.wait_for_selector(".picker")
        self.rows(page).nth(0).click()
        page.click(".picker-save")
        self.assertTrue(page.locator(".deck-end").is_visible())
        self.assertEqual(len(self.cookie().split(",")), 1)

    def test_the_limit_drops_the_oldest(self):
        old = ",".join(str(n) for n in range(900000, 900300))
        page = self.open_deck(cookie=old)
        self.skip_to_belly(page)
        page.click(".deck-add")
        self.rows(page).nth(0).click()
        page.click(".picker-save")
        ids = self.cookie().split(",")
        self.assertEqual(len(ids), 300)
        self.assertEqual(ids[0], str(self.belly_events()[0]))
        self.assertNotIn("900299", ids)

    def test_applying_a_change_does_not_make_the_document_observer_loop(self):
        page = self.open_picker()
        page.evaluate(
            "() => { window.mutations = 0; new MutationObserver(r => { window.mutations += r.length; })"
            ".observe(document.documentElement, {childList: true, subtree: true, attributes: true, characterData: true}); }"
        )
        self.rows(page).nth(0).click()
        page.click(".picker-save")
        page.wait_for_timeout(600)
        self.assertLess(page.evaluate("() => window.mutations"), 60)

    def test_the_picker_is_a_dialog_with_focus_kept_and_returned(self):
        page = self.open_picker()
        self.assertEqual(page.get_attribute(".picker", "role"), "dialog")
        self.assertTrue(page.evaluate("() => document.querySelector('.picker').contains(document.activeElement)"))
        page.click(".picker-close")
        self.assertEqual(page.evaluate("() => document.activeElement.className"), "deck-add")

    def test_the_existing_save_api_takes_a_change_from_the_page(self):
        page = self.open_deck(cookie="5,6")
        ids = page.evaluate("() => window.SavedShows.apply(['7', '5'], ['6'])")
        self.assertEqual(ids, ["7", "5"])
        self.assertEqual(self.cookie(), "7,5")


class PlayerTestCase(DeckBrowserTestCase):
    def frames(self, page):
        return page.eval_on_selector_all(".discover-card:not([hidden]) iframe", "frames => frames.map(f => f.src)")

    def only_belly(self, services):
        self.make_deck(services)
        page = self.open_deck(services)
        self.skip_to_belly(page)
        return page

    def test_video_first(self):
        page = self.only_belly(("youtube", "apple", "spotify"))
        self.assertEqual(self.frames(page), ["https://www.youtube-nocookie.com/embed/vid123"])
        self.assertEqual(page.locator(".discover-card:not([hidden]) a.apple-play").count(), 1)
        self.assertEqual(self.requests_to("apple.com", "spotify.com"), [])
        # not started by the page
        self.assertNotIn("autoplay=1", self.frames(page)[0])

    def test_apple_music_before_spotify(self):
        page = self.only_belly(("apple", "spotify"))
        self.assertEqual(self.frames(page), ["https://embed.music.apple.com/us/album/300?i=200"])
        self.assertEqual(page.locator(".discover-card:not([hidden]) a.spotify-play").count(), 1)
        self.assertEqual(self.requests_to("spotify.com"), [])

    def test_spotify_only_loads_its_player(self):
        page = self.only_belly(("spotify",))
        self.assertEqual(self.frames(page), ["https://open.spotify.com/embed/artist/sp123"])
        self.assertTrue(self.requests_to("open.spotify.com"))

    def test_apple_only(self):
        page = self.only_belly(("apple",))
        self.assertEqual(self.frames(page), ["https://embed.music.apple.com/us/album/300?i=200"])

    def test_no_match_has_no_player(self):
        page = self.only_belly(())
        self.assertEqual(self.frames(page), [])
        self.assertEqual(page.locator(".discover-card:not([hidden]) a.youtube-play").count(), 0)
        self.assertEqual(self.requests_to("youtube", "apple.com", "spotify.com"), [])

    def test_only_the_top_card_has_a_player_and_a_passed_one_loses_it(self):
        self.make_deck(("youtube",))
        page = self.open_deck(("youtube",))
        # Anjimile is on top and has no match: nothing yet, though Belly's is on the page
        self.assertEqual(page.locator("iframe").count(), 0)
        self.assertEqual(self.requests_to("youtube"), [])
        self.skip_to_belly(page)
        self.assertEqual(page.locator("iframe").count(), 1)
        page.click(".deck-skip")
        page.wait_for_function("() => document.querySelector('.discover-card:not([hidden])').dataset.act === 'Cheap Trick'")
        self.assertEqual(page.locator("iframe").count(), 0)

    def test_pressing_the_cards_own_button_replaces_its_player(self):
        page = self.only_belly(("youtube", "apple", "spotify"))
        card = ".discover-card:not([hidden])"
        page.click(f"{card} a.apple-play")
        self.assertEqual(self.frames(page), ["https://embed.music.apple.com/us/album/300?i=200"])
        marked = page.evaluate("() => { const f = document.querySelector('.discover-card:not([hidden]) iframe'); f.dataset.same = '1'; return true; }")
        self.assertTrue(marked)
        page.click(f"{card} a.apple-play")
        # the one already shown stays in place
        self.assertEqual(page.locator(f"{card} iframe[data-same]").count(), 1)
        page.click(f"{card} a.spotify-play")
        self.assertEqual(self.frames(page), ["https://open.spotify.com/embed/artist/sp123"])
        page.click(f"{card} a.youtube-play")
        self.assertEqual(self.frames(page), ["https://www.youtube-nocookie.com/embed/vid123"])
        self.assertEqual(page.url, self.live_server_url + "/discover")

    def test_the_player_is_big_enough_and_nothing_is_over_it_on_a_phone(self):
        self.make_deck()
        page = self.open_deck(width=390)
        self.skip_to_belly(page)
        # the hint is up and the card swaying: still nothing over the box
        box = page.locator(".discover-card:not([hidden]) .discover-player-box").bounding_box()
        self.assertGreaterEqual(box["width"], 200)
        self.assertGreaterEqual(box["height"], 200)
        for stage in range(2):
            covered = page.evaluate(
                """() => {
                  const box = document.querySelector('.discover-card:not([hidden]) .discover-player-box');
                  const r = box.getBoundingClientRect();
                  const points = [[.5, .5], [.1, .1], [.9, .1], [.1, .9], [.9, .9]];
                  return points.filter(([x, y]) => {
                    const hit = document.elementFromPoint(r.left + r.width * x, r.top + r.height * y);
                    return !hit || !box.contains(hit);
                  }).length;
                }"""
            )
            self.assertEqual(covered, 0)
            # and none of the page's other parts has its box inside this one
            overlapping = page.evaluate(
                """() => {
                  const box = document.querySelector('.discover-card:not([hidden]) .discover-player-box');
                  const r = box.getBoundingClientRect();
                  return Array.from(document.querySelectorAll('.discover *')).filter(el => {
                    if (el.contains(box) || box.contains(el)) return false;
                    const e = el.getBoundingClientRect();
                    if (e.width <= 1 || e.height <= 1 || getComputedStyle(el).display === 'none') return false;
                    return e.left < r.right && e.right > r.left && e.top < r.bottom && e.bottom > r.top;
                  }).map(el => el.className);
                }"""
            )
            self.assertEqual(overlapping, [])
            page.wait_for_timeout(600)

    def test_every_service_has_a_box_of_at_least_200_by_200(self):
        for services in (("apple",), ("spotify",)):
            Band.objects.all().delete()
            page = self.only_belly(services)
            box = page.locator(".discover-card:not([hidden]) iframe").bounding_box()
            self.assertGreaterEqual(box["width"], 200)
            self.assertGreaterEqual(box["height"], 200)

    def test_touching_the_player_does_not_swipe(self):
        page = self.only_belly(("youtube",))
        box = page.locator(".discover-card:not([hidden]) .discover-player-box").bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 150, y, steps=6)
        page.mouse.move(x - 300, y, steps=6)
        page.mouse.up()
        page.wait_for_timeout(300)
        self.assertEqual(self.shown(page), "Belly")
        self.assertEqual(page.locator(".picker").count(), 0)

    def test_the_listings_players_are_unchanged(self):
        # the listing's builders, with no height, keep their sizes
        _, page = self.open_page("/")
        sizes = page.evaluate(
            """() => {
              const button = document.createElement('a');
              button.dataset.spotifyArtist = 'x'; button.dataset.appleSong = '1'; button.dataset.appleAlbum = '2';
              button.dataset.youtubeVideo = 'v'; button.dataset.artistName = 'n'; button.href = '#';
              return [ArtistPreview.spotifyPlayer(button).height,
                ArtistPreview.applePlayer(button).querySelector('iframe').height,
                ArtistPreview.youtubePlayer(button).querySelector('iframe').getAttribute('height')];
            }"""
        )
        self.assertEqual(sizes, ["152", "175", None])


class HintTestCase(DeckBrowserTestCase):
    def test_the_hint_shows_until_the_first_button(self):
        page = self.open_deck()
        self.assertTrue(page.locator(".hint-skip").is_visible())
        self.assertEqual(page.inner_text(".hint-skip"), "← Skip")
        self.assertEqual(page.inner_text(".hint-add"), "Add →")
        self.assertNotEqual(page.eval_on_selector(".discover-card:not([hidden])", "c => getComputedStyle(c).animationName"), "none")
        page.click(".deck-skip")
        self.assertFalse(page.locator(".deck-hint").is_visible())
        self.assertEqual(page.eval_on_selector(".discover-card:not([hidden])", "c => getComputedStyle(c).animationName"), "none")

    def test_the_first_swipe_stops_it(self):
        page = self.open_deck()
        box = page.locator(".discover-card:not([hidden]) .discover-name").bounding_box()
        x, y = box["x"] + 10, box["y"] + 5
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x - 20, y, steps=3)
        self.assertFalse(page.locator(".deck-hint").is_visible())
        page.mouse.up()

    def test_it_is_stored_nowhere(self):
        page = self.open_deck()
        page.click(".deck-skip")
        page.reload()
        self.assertTrue(page.locator(".hint-skip").is_visible())
        self.assertEqual(page.evaluate("() => localStorage.length + sessionStorage.length"), 0)
        self.assertNotIn("hint", page.evaluate("() => document.cookie"))

    def test_reduced_motion_shows_the_labels_without_movement(self):
        page = self.open_deck(reduced_motion=True)
        self.assertTrue(page.locator(".hint-skip").is_visible())
        self.assertTrue(page.locator(".hint-add").is_visible())
        self.assertEqual(page.eval_on_selector(".discover-card:not([hidden])", "c => getComputedStyle(c).animationName"), "none")


class AccessTestCase(DeckBrowserTestCase):
    def test_keyboard_only(self):
        page = self.open_deck()
        page.keyboard.press("ArrowLeft")
        page.wait_for_function("() => document.querySelector('.discover-card:not([hidden])').dataset.act === 'Belly'")
        page.keyboard.press("ArrowRight")
        page.wait_for_selector(".picker")
        # focus is in the picker: space ticks the first row, the button is reached by tab
        self.assertTrue(page.evaluate("() => document.activeElement.matches('.picker input')"))
        page.keyboard.press("Space")
        self.assertEqual(page.inner_text(".picker-save"), "Save 1 show")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")
        self.assertEqual(page.evaluate("() => document.activeElement.className"), "picker-save")
        page.keyboard.press("Enter")
        self.assertEqual(len(self.cookie().split(",")), 1)
        self.assertEqual(self.shown(page), "Cheap Trick")
        # the picker closes with escape too
        page.keyboard.press("ArrowRight")
        page.wait_for_selector(".picker")
        page.keyboard.press("Escape")
        self.assertEqual(page.locator(".picker").count(), 0)

    def test_the_controls_are_named(self):
        page = self.open_deck()
        self.assertEqual(page.get_attribute(".deck-skip", "aria-label"), "Skip this act")
        self.assertEqual(page.get_attribute(".deck-add", "aria-label"), "Add this act's shows")

    def test_the_card_change_is_announced(self):
        page = self.open_deck()
        self.assertEqual(page.get_attribute(".deck-live", "aria-live"), "polite")
        self.assertIn("Anjimile", page.inner_text(".deck-live"))
        page.click(".deck-skip")
        page.wait_for_function("() => document.querySelector('.deck-live').textContent.includes('Belly')")
