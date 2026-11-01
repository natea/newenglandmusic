"""
the a-z index on a phone, in a real browser: 390px wide, nothing scrolls sideways and the
letter rail wraps (core/tests/browser.py keeps it offline).
"""

from core.models import Artist, Band
from core.tests.browser import BrowserTestCase


class ActIndexPhoneTestCase(BrowserTestCase):
    def test_on_a_phone(self):
        Band.objects.create(name="Belly", city_town="Providence", state="RI")
        Artist.objects.create(name="A Very Long Artist Name That Goes On And On Without Stopping", area="United States")
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        _, page = self.open_page("/bands", context=context)
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
        rail = page.locator(".index-rail").bounding_box()
        self.assertLessEqual(rail["x"] + rail["width"], 390)
        # 27 letters don't fit one line at this width: the rail wraps onto a second
        letter = page.locator(".index-rail a").first.bounding_box()
        self.assertGreater(rail["height"], 1.8 * letter["height"])
        self.assertEqual(self.blocked, [])
