"""
the discovery deck's YouTube player, driven over its message channel, in a real browser. the
embed's address is routed to a local stub page that records the commands it is sent and says
what a test makes it say, so nothing reaches YouTube (see YOUTUBE_STUB in
core/tests/test_discover_browser.py).
"""

from core.tests import test_discover_browser as base


class YouTubePlayerTestCase(base.DeckBrowserTestCase):
    stub_youtube_embed = True

    def embed(self, page):
        # the frame has its address once its stub page has been fetched
        for _ in range(50):
            frames = [frame for frame in page.frames if "youtube-nocookie.com" in frame.url]
            if frames:
                break
            page.wait_for_timeout(100)
        self.assertEqual(len(frames), 1)
        frames[0].wait_for_load_state()
        return frames[0]

    def frames(self, page):
        return page.eval_on_selector_all(".discover-card:not([hidden]) iframe", "frames => frames.map(f => f.src)")

    def say(self, frame, message):
        frame.evaluate("message => window.say(message)", message)

    def commands(self, frame):
        return frame.evaluate("() => window.commands")

    def open_clocked(self, width=None):
        self.video_deck()
        page = self.open_deck(clock=True, width=width)
        frame = self.embed(page)
        # the clock runs by itself until paused, so the waits below are exact
        page.wait_for_timeout(100)
        page.clock.pause_at(page.evaluate("Date.now()") / 1000 + 0.05)
        return page, frame

    def wait_for_card(self, page, act):
        page.wait_for_function(
            "name => document.querySelector('.discover-card:not([hidden])')?.dataset.act === name", arg=act
        )


class PlayerApiAddressTestCase(YouTubePlayerTestCase):
    def test_the_decks_player_carries_the_api_parameters(self):
        self.video_deck()
        page = self.open_deck()
        src = page.eval_on_selector(".discover-card:not([hidden]) iframe", "f => f.src")
        self.assertEqual(src, self.autoplay_src("vid123"))
        for part in ("autoplay=1", "playsinline=1", "enablejsapi=1"):
            self.assertIn(part, src)
        self.assertIn("origin=" + self.live_server_url.replace(":", "%3A").replace("/", "%2F"), src)

    def test_the_listings_player_carries_none_of_them(self):
        self.video_deck()
        _, page = self.open_page("/")
        frame = page.evaluate(
            """() => {
              const button = document.createElement('a');
              button.dataset.youtubeVideo = 'v'; button.dataset.artistName = 'n'; button.href = '#';
              return ArtistPreview.youtubePlayer(button).querySelector('iframe').src;
            }"""
        )
        for part in ("autoplay", "enablejsapi", "origin"):
            self.assertNotIn(part, frame)
        # and the listing's click builds no message listening on the page's side
        self.assertEqual(page.locator("iframe").count(), 0)


class PlayCommandTestCase(YouTubePlayerTestCase):
    def test_the_page_says_it_is_listening_once_the_frame_loads(self):
        self.video_deck()
        page = self.open_deck()
        frame = self.embed(page)
        frame.wait_for_function("() => window.heard.length > 0")
        self.assertEqual(frame.evaluate("() => window.heard"), ["listening"])

    def test_a_ready_player_is_told_to_play(self):
        self.video_deck()
        page = self.open_deck()
        frame = self.embed(page)
        self.assertEqual(self.commands(frame), [])
        self.say(frame, {"event": "onReady"})
        frame.wait_for_function("() => window.commands.length > 0")
        self.assertEqual(self.commands(frame), ["playVideo"])

    def test_a_passed_card_is_not_told_to_play(self):
        self.video_deck()
        page = self.open_deck()
        old = self.embed(page)
        page.click(".deck-skip")
        self.wait_for_card(page, "Anjimile")
        page.wait_for_timeout(300)
        self.assertTrue(old.is_detached())
        # the new top card's player is the one listened to
        new = self.embed(page)
        self.say(new, {"event": "onReady"})
        new.wait_for_function("() => window.commands.length > 0")
        self.assertEqual(self.commands(new), ["playVideo"])
        self.assertEqual(page.locator("iframe").count(), 1)

    def test_a_message_from_elsewhere_is_ignored(self):
        self.video_deck()
        page = self.open_deck()
        frame = self.embed(page)
        # the page's own window is not the top card's frame, even with the right text
        page.evaluate("() => window.postMessage(JSON.stringify({event: 'onReady'}), '*')")
        page.wait_for_timeout(200)
        self.assertEqual(self.commands(frame), [])
        # nor is a frame of another origin that is not youtube's
        page.evaluate(
            """() => { const f = document.createElement('iframe'); f.srcdoc =
              '<script>parent.postMessage(JSON.stringify({event: "onReady"}), "*")<\\/script>';
              document.body.appendChild(f); }"""
        )
        page.wait_for_timeout(300)
        self.assertEqual(self.commands(frame), [])


class DidItStartTestCase(YouTubePlayerTestCase):
    LINE = ".discover-card:not([hidden]) .deck-play-line"

    def ready(self, frame):
        self.say(frame, {"event": "onReady"})
        frame.wait_for_function("() => window.commands.length > 0")

    def line(self, page):
        return page.locator(self.LINE).inner_text()

    def test_retry_once(self):
        page, frame = self.open_clocked()
        self.ready(frame)
        page.clock.run_for(3900)
        self.assertEqual(self.commands(frame), ["playVideo"])
        page.clock.run_for(200)
        frame.wait_for_function("() => window.commands.length === 2")
        page.clock.run_for(30000)
        page.wait_for_timeout(200)
        self.assertEqual(self.commands(frame), ["playVideo", "playVideo"])

    def test_the_line_appears_below_the_player(self):
        page, frame = self.open_clocked(width=390)
        self.ready(frame)
        page.clock.run_for(4000)
        page.clock.run_for(2900)
        self.assertEqual(self.line(page), "")
        page.clock.run_for(200)
        self.assertIn("Press play", self.line(page))
        self.assertEqual(page.locator(self.LINE).get_attribute("aria-live"), "polite")
        self.assertEqual(page.locator(self.LINE).get_attribute("role"), "status")
        # below the player's box, and nothing is drawn over the player
        box = page.locator(".discover-card:not([hidden]) .discover-player-box").bounding_box()
        line = page.locator(self.LINE).bounding_box()
        self.assertGreaterEqual(line["y"], box["y"] + box["height"] - 1)
        frame_box = page.locator(".discover-card:not([hidden]) iframe").bounding_box()
        self.assertGreaterEqual(frame_box["width"], 200)
        covered = page.evaluate(
            """b => {
              for (const fx of [0.1, 0.5, 0.9]) {
                for (const fy of [0.1, 0.5, 0.9]) {
                  const hit = document.elementFromPoint(b.x + b.width * fx, b.y + b.height * fy);
                  if (!hit || hit.tagName !== 'IFRAME') { return hit ? hit.className || hit.tagName : 'nothing'; }
                }
              }
              return null;
            }""",
            frame_box,
        )
        self.assertIsNone(covered)

    def test_the_line_goes_when_playing_starts(self):
        page, frame = self.open_clocked()
        self.ready(frame)
        page.clock.run_for(7100)
        self.assertIn("Press play", self.line(page))
        self.say(frame, {"event": "onStateChange", "info": 1})
        page.wait_for_function("sel => !document.querySelector(sel).textContent", arg=self.LINE)

    def test_a_player_that_never_reports_ready(self):
        page, frame = self.open_clocked()
        # the 7 seconds run from the frame's load, a little before the clock was paused
        page.clock.run_for(6500)
        self.assertEqual(self.line(page), "")
        page.clock.run_for(1000)
        self.assertIn("Press play", self.line(page))
        self.assertEqual(self.commands(frame), [])
        self.say(frame, {"event": "infoDelivery", "info": {"playerState": 1}})
        page.wait_for_function("sel => !document.querySelector(sel).textContent", arg=self.LINE)

    def test_no_line_when_it_plays(self):
        page, frame = self.open_clocked()
        self.ready(frame)
        self.say(frame, {"event": "onStateChange", "info": 1})
        page.wait_for_timeout(200)
        page.clock.run_for(30000)
        page.wait_for_timeout(200)
        self.assertEqual(self.commands(frame), ["playVideo"])
        self.assertEqual(self.line(page), "")

    def test_the_line_goes_when_the_card_leaves_the_top(self):
        page, frame = self.open_clocked()
        self.ready(frame)
        page.clock.run_for(7100)
        page.click(".deck-skip")
        page.clock.run_for(500)
        self.wait_for_card(page, "Anjimile")
        self.assertEqual(page.locator(".deck-play-line:not(:empty)").count(), 0)


class UnplayableTestCase(YouTubePlayerTestCase):
    def test_embedding_not_allowed_and_not_found(self):
        for code in (101, 150, 100):
            with self.subTest(code=code):
                self.clear_acts()
                self.video_deck()
                page = self.open_deck()
                frame = self.embed(page)
                self.say(frame, {"event": "onError", "info": code})
                page.wait_for_selector(".discover-unplayable")
                self.assertEqual(page.locator(".discover-card:not([hidden]) iframe").count(), 0)
                link = page.locator(".discover-unplayable a")
                self.assertEqual(link.get_attribute("href"), "https://www.youtube.com/watch?v=vid123")
                self.assertEqual(link.get_attribute("target"), "_blank")
                # the card still works
                page.click(".deck-add")
                self.assertEqual(page.locator(".picker").count(), 1)
                page.click(".picker-close")
                page.click(".deck-skip")
                self.wait_for_card(page, "Anjimile")

    def test_a_channel_match_links_the_channel(self):
        from core.models import YouTubeArtistLink

        self.video_deck()
        YouTubeArtistLink.objects.filter(name_key="aardvark").update(video_id="")
        page = self.open_deck()
        self.say(self.embed(page), {"event": "onError", "info": 101})
        page.wait_for_selector(".discover-unplayable")
        link = page.locator(".discover-unplayable a")
        self.assertEqual(link.get_attribute("href"), "https://www.youtube.com/channel/UCchannel")

    def test_other_errors_leave_the_player(self):
        self.video_deck()
        page = self.open_deck()
        self.say(self.embed(page), {"event": "onError", "info": 2})
        page.wait_for_timeout(300)
        self.assertEqual(page.locator(".discover-unplayable").count(), 0)
        self.assertEqual(page.locator(".discover-card:not([hidden]) iframe").count(), 1)


class InsideTheVisitorsActionTestCase(YouTubePlayerTestCase):
    """the clock is paused, so the slide-off never ends unless a test runs it"""

    def test_the_next_player_exists_before_the_animation_ends(self):
        page, old = self.open_clocked()
        page.click(".deck-skip")
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertEqual(page.locator(".deck-ghost").count(), 1)
        self.assertEqual(page.locator(".deck-ghost iframe").count(), 0)
        self.assertEqual(page.locator("iframe").count(), 1)
        self.assertEqual(self.frames(page), [self.autoplay_src("vid123")])
        self.assertTrue(old.is_detached())
        page.clock.run_for(300)
        self.assertEqual(page.locator(".deck-ghost").count(), 0)
        self.assertEqual(page.locator("iframe").count(), 1)

    def test_the_swipe_and_the_key_do_the_same(self):
        for how in ("key", "swipe"):
            with self.subTest(how=how):
                self.clear_acts()
                page, old = self.open_clocked()
                if how == "key":
                    page.keyboard.press("ArrowLeft")
                else:
                    box = page.locator(".discover-card:not([hidden]) .discover-name").bounding_box()
                    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                    page.mouse.move(x, y)
                    page.mouse.down()
                    page.mouse.move(x - 100, y, steps=4)
                    page.mouse.move(x - 200, y, steps=4)
                    page.mouse.up()
                self.assertEqual(self.shown(page), "Anjimile")
                self.assertEqual(self.frames(page), [self.autoplay_src("vid123")])
                self.assertEqual(page.locator(".deck-ghost").count(), 1)

    def test_only_the_new_top_card_is_listened_to(self):
        page, old = self.open_clocked()
        page.click(".deck-skip")
        new = self.embed(page)
        self.assertNotEqual(new, old)
        self.say(new, {"event": "onReady"})
        new.wait_for_function("() => window.commands.length > 0")
        self.assertEqual(self.commands(new), ["playVideo"])
        self.assertTrue(old.is_detached())

    def test_a_double_press_or_held_key_moves_once(self):
        page, _ = self.open_clocked()
        page.click(".deck-skip")
        page.click(".deck-skip", force=True)
        for _ in range(3):
            page.keyboard.press("ArrowLeft")
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertEqual(page.locator("iframe").count(), 1)
        page.clock.run_for(300)
        self.assertEqual(self.shown(page), "Anjimile")
        # and the deck moves again once the slide-off has ended
        page.keyboard.press("ArrowLeft")
        self.assertEqual(self.shown(page), "Belly")

    def test_reduced_motion(self):
        self.video_deck()
        page = self.open_deck(reduced_motion=True)
        page.click(".deck-skip")
        self.assertEqual(self.shown(page), "Anjimile")
        self.assertEqual(page.locator(".deck-ghost").count(), 0)
        self.assertEqual(self.frames(page), [self.autoplay_src("vid123")])
        self.assertEqual(page.locator("iframe").count(), 1)
        page.keyboard.press("ArrowLeft")
        self.assertEqual(self.shown(page), "Belly")
