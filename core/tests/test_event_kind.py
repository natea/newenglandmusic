from core.models import Event
from django.test import SimpleTestCase


class EventKindTestCase(SimpleTestCase):
    def test_music_kinds(self):
        for kind in ("live_music", "dj_dance", "open_mic"):
            self.assertTrue(Event(kind=kind).is_music_kind, kind)

    def test_non_music_kinds(self):
        for kind in ("karaoke", "comedy", "other"):
            self.assertFalse(Event(kind=kind).is_music_kind, kind)

    def test_unlabelled_counts_as_music(self):
        self.assertTrue(Event().is_music_kind)
