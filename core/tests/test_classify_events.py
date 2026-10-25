import datetime
import os
from io import StringIO
from unittest import mock

from core.management.commands import classify_events
from core.models import Event, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone


class ClassifyEventsTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name="Aura", city_town="Portland", state="ME")
        self.labels = {}
        self.requests = []
        self.errors = []
        env = mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"})
        env.start()
        self.addCleanup(env.stop)
        anthropic_client = mock.patch("anthropic.Anthropic")
        anthropic_client.start()
        self.addCleanup(anthropic_client.stop)

        def classify(client, items, model):
            self.requests.append(items)
            return [self.labels.get(i["title"], "live_music") for i in items], self.errors, (10, 1)

        patcher = mock.patch.object(classify_events, "classify", classify)
        patcher.start()
        self.addCleanup(patcher.stop)

    def event(self, title, days=7, **fields):
        fields.setdefault("source", "ical")
        fields.setdefault("is_approved", False)
        return Event.all_objects.create(
            title=title,
            starttime=timezone.now() + datetime.timedelta(days=days),
            venue=self.venue,
            **fields,
        )

    def run_command(self, *args):
        out = StringIO()
        call_command("classify_events", *args, stdout=out)
        return out.getvalue()

    def test_labels_upcoming_unlabelled_imported_events(self):
        band = self.event("Band")
        trivia = self.event("Trivia Night")
        past = self.event("Last month", days=-30)
        submitted = self.event("User submitted", source="")
        already = self.event("Already", kind="comedy", kind_set_by="ai")
        admin = self.event("Admin cleared", kind="", kind_set_by="admin")
        self.labels = {"Trivia Night": "other"}

        output = self.run_command()

        self.assertEqual([i["title"] for i in self.requests[0]], ["Band", "Trivia Night"])
        self.assertEqual(self.requests[0][0]["venue"], "Aura (Portland, ME)")
        def kind(event):
            return Event.all_objects.get(pk=event.pk).kind
        self.assertEqual((kind(band), kind(trivia)), ("live_music", "other"))
        self.assertEqual(Event.all_objects.get(pk=band.pk).kind_set_by, "ai")
        for untouched, expected in ((past, ""), (submitted, ""), (already, "comedy"), (admin, "")):
            self.assertEqual(kind(untouched), expected, untouched.title)
        self.assertIn("not music, hidden from review (1)", output)
        self.assertIn("Aura (Portland, ME)\n      Trivia Night [other]", output)
        self.assertIn("1 live_music, 1 other", output)

    def test_dry_run_saves_nothing(self):
        trivia = self.event("Trivia Night")
        self.labels = {"Trivia Night": "other"}
        output = self.run_command("--dry-run")
        self.assertEqual(Event.all_objects.get(pk=trivia.pk).kind, "")
        self.assertIn("[dry run] not music, would be hidden from review (1)", output)
        self.assertIn("Trivia Night [other]", output)

    def test_limit(self):
        for i in range(5):
            self.event(f"Show {i}", days=i + 1)
        self.run_command("--limit", "2")
        self.assertEqual([i["title"] for i in self.requests[0]], ["Show 0", "Show 1"])

    def test_failed_batch_is_reported_and_left_unlabelled(self):
        show = self.event("Show")
        self.labels = {"Show": ""}
        self.errors = ["labelling events 1-1 failed: overloaded"]
        output = self.run_command()
        self.assertEqual(Event.all_objects.get(pk=show.pk).kind, "")
        self.assertIn("labelling events 1-1 failed: overloaded", output)
        self.assertIn("1 unlabelled", output)

    def test_nothing_to_label(self):
        self.assertIn("no events to label", self.run_command())
        self.assertEqual(self.requests, [])

    def test_missing_api_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "ANTHROPIC_API_KEY is not set"):
                self.run_command()
