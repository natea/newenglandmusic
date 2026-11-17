from core.tests.browser import BrowserTestCase
from core.tests.geo_fixture import load_geo_fixture


class GrowingInputsTestCase(BrowserTestCase):
    """typing in the last empty town or venue input adds another, so any number can be followed"""

    def setUp(self):
        super().setUp()
        load_geo_fixture()

    def count(self, page, kind):
        return page.locator(f'input[name="{kind}"]').count()

    def test_a_new_input_appears_when_the_last_is_filled(self):
        _, page = self.open_page("/digest")
        for kind, values in (("town", ["Somerville, MA", "Medford, MA", "Cambridge, MA"]), ("venue", ["Once", "The Burren", "Lilypad"])):
            with self.subTest(kind):
                self.assertEqual(self.count(page, kind), 2)
                inputs = page.locator(f'input[name="{kind}"]')
                inputs.nth(0).fill(values[0])
                # the first isn't the last, so nothing is added yet
                self.assertEqual(self.count(page, kind), 2)
                inputs.nth(1).fill(values[1])
                self.assertEqual(self.count(page, kind), 3)
                inputs.nth(2).fill(values[2])
                self.assertEqual(self.count(page, kind), 4)
                self.assertEqual(inputs.nth(3).input_value(), "")

    def test_without_javascript_two_empty_inputs(self):
        _, page = self.open_page("/digest", javascript=False)
        self.assertEqual(self.count(page, "town"), 2)
        self.assertEqual(self.count(page, "venue"), 2)
