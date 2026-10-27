"""
a base for tests in a real browser (playwright's headless chromium) against django's live
test server. every request that isn't to the test server is aborted and remembered in
self.blocked, so the suite stays offline.

needs `python -m playwright install chromium` once (ci does it).
"""

from unittest import mock

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


class BrowserTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # playwright's sync api runs an event loop, which django's orm refuses without this
        cls.async_unsafe = mock.patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
        cls.async_unsafe.start()
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except PlaywrightError as e:
            cls.playwright.stop()
            super().tearDownClass()
            cls.async_unsafe.stop()
            # fail, not skip: a skipped test isn't a passing one
            raise AssertionError(
                f"chromium isn't installed for playwright: run `python -m playwright install chromium` ({e})"
            )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
        cls.async_unsafe.stop()

    def setUp(self):
        super().setUp()
        self.blocked = []

    def open_page(self, path="/", javascript=True, context=None):
        if context is None:
            context = self.browser.new_context(java_script_enabled=javascript)
            self.addCleanup(context.close)
            context.route("**/*", self.only_the_test_server)
        page = context.new_page()
        page.goto(self.live_server_url + path)
        return context, page

    def only_the_test_server(self, route):
        if route.request.url.startswith(self.live_server_url):
            route.continue_()
        else:
            self.blocked.append(route.request.url)
            route.abort()
