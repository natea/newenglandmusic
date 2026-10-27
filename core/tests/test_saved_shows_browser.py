"""
saving shows in a real browser: the SAVE links, the saved_shows cookie and the header's
count, which only javascript sets. see core/tests/browser.py.
"""

import datetime
from urllib.parse import unquote

from core.models import Event
from core.saved_shows import COOKIE_NAME, MAX_SAVED
from core.tests.browser import BrowserTestCase
from django.utils import timezone


class SavedShowsBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        self.first = Event.objects.create(title="first show", starttime=tomorrow)
        self.second = Event.objects.create(title="second show", starttime=tomorrow + datetime.timedelta(hours=1))

    def save_link(self, page, event):
        return page.locator(f"#event-{event.pk} a.save")

    def saved_cookie(self, context):
        for cookie in context.cookies():
            if cookie["name"] == COOKIE_NAME:
                return unquote(cookie["value"])
        return None

    def count(self, page):
        return page.locator("a.saved-count").inner_text()

    def test_save_a_show(self):
        context, page = self.open_page()
        link = self.save_link(page, self.first)
        self.assertEqual(link.inner_text(), "SAVE")
        link.click()
        self.assertEqual(link.inner_text(), "SAVED")
        self.assertEqual(link.get_attribute("aria-pressed"), "true")
        self.assertEqual(self.saved_cookie(context), str(self.first.pk))

    def test_unsave_a_show(self):
        context, page = self.open_page()
        link = self.save_link(page, self.first)
        link.click()
        link.click()
        self.assertEqual(link.inner_text(), "SAVE")
        self.assertEqual(self.saved_cookie(context), "")

    def test_newest_saved_first(self):
        context, page = self.open_page()
        self.save_link(page, self.first).click()
        self.save_link(page, self.second).click()
        self.assertEqual(self.saved_cookie(context), f"{self.second.pk},{self.first.pk}")

    def test_saved_state_shown_on_load(self):
        context, page = self.open_page()
        self.save_link(page, self.second).click()
        _, again = self.open_page(context=context)
        self.assertEqual(self.save_link(again, self.second).inner_text(), "SAVED")
        self.assertEqual(self.save_link(again, self.first).inner_text(), "SAVE")

    def test_every_copy_of_the_event_updates(self):
        _, page = self.open_page()
        # copy the event as the day map's panel does
        page.evaluate(
            f"""() => {{
                const copy = document.querySelector('#event-{self.first.pk}').cloneNode(true);
                copy.id = 'map-copy';
                document.body.appendChild(copy);
            }}"""
        )
        copy = page.locator("#map-copy a.save")
        copy.wait_for(state="visible")
        self.save_link(page, self.first).click()
        self.assertEqual(copy.inner_text(), "SAVED")
        # and saving from the copy updates the listing's
        copy.click()
        self.assertEqual(self.save_link(page, self.first).inner_text(), "SAVE")

    def test_no_javascript(self):
        _, page = self.open_page(javascript=False)
        self.assertFalse(self.save_link(page, self.first).is_visible())
        self.assertEqual(self.count(page), "Saved shows")

    def test_count_shown_and_updated(self):
        _, page = self.open_page()
        self.assertEqual(self.count(page), "Saved shows")
        self.save_link(page, self.first).click()
        self.assertEqual(self.count(page), "Saved shows (1)")
        self.save_link(page, self.second).click()
        self.assertEqual(self.count(page), "Saved shows (2)")
        self.save_link(page, self.second).click()
        self.assertEqual(self.count(page), "Saved shows (1)")

    def test_limit_drops_the_oldest(self):
        context, page = self.open_page()
        # 300 shows already saved, oldest last
        full = [str(100000 + n) for n in range(MAX_SAVED)]
        context.add_cookies([{"name": COOKIE_NAME, "value": ",".join(full), "url": self.live_server_url}])
        _, page = self.open_page(context=context)
        self.save_link(page, self.first).click()
        saved = self.saved_cookie(context).split(",")
        self.assertEqual(len(saved), MAX_SAVED)
        self.assertEqual(saved[0], str(self.first.pk))
        self.assertNotIn(full[-1], saved)

    def test_saved_page_lists_what_was_saved(self):
        context, page = self.open_page()
        self.save_link(page, self.second).click()
        self.save_link(page, self.first).click()
        _, saved = self.open_page("/saved", context=context)
        # both, as the browser wrote them (commas encoded), in start-time order
        self.assertEqual(saved.locator("div.event").count(), 2)
        self.assertIn("first show", saved.locator("div.event").nth(0).inner_text())
        self.assertIn("second show", saved.locator("div.event").nth(1).inner_text())
        self.assertEqual(self.save_link(saved, self.second).inner_text(), "SAVED")
        self.assertEqual(self.count(saved), "Saved shows (2)")
        # the page kept the cookie as it was
        self.assertEqual(self.saved_cookie(context), f"{self.first.pk},{self.second.pk}")
