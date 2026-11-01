from core.search_marks import mark_match, match_span
from django.test import SimpleTestCase


class MatchSpanTestCase(SimpleTestCase):
    def test_case_accents_and_punctuation(self):
        self.assertEqual(mark_match("Belly", "bel"), "<mark>Bel</mark>ly")
        self.assertEqual(mark_match("Béla Fleck", "bel"), "<mark>Bél</mark>a Fleck")
        self.assertEqual(mark_match("O'Brien's Pub", "obr"), "<mark>O&#x27;Br</mark>ien&#x27;s Pub")
        self.assertEqual(mark_match("Dan Campbell", "BEL"), "Dan Camp<mark>bel</mark>l")

    def test_across_words(self):
        self.assertEqual(mark_match("Blue October", "blue o"), "<mark>Blue O</mark>ctober")

    def test_nothing_to_mark(self):
        self.assertIsNone(match_span("Belly", "zz"))
        self.assertIsNone(match_span("Belly", "  "))
        self.assertEqual(mark_match("<b>Belly</b>", "zz"), "&lt;b&gt;Belly&lt;/b&gt;")

    def test_escaped_around_the_mark(self):
        self.assertEqual(mark_match("Tom & Belly", "bel"), "Tom &amp; <mark>Bel</mark>ly")
