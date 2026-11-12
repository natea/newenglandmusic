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

    def say(self, frame, message):
        frame.evaluate("message => window.say(message)", message)

    def commands(self, frame):
        return frame.evaluate("() => window.commands")

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
