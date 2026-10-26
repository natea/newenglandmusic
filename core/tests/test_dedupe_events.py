import datetime
from io import StringIO

from core.models import Event, JobRun, Venue, VenueFetchStatus
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


class DedupeEventsTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V0019", name="Arch Street Tavern", state="CT")
        self.start = (timezone.now() + datetime.timedelta(days=4)).replace(microsecond=0)
        self.created = timezone.now() - datetime.timedelta(days=2)

    def copy(self, external_id, source, age_days=0, **fields):
        values = dict(
            title="Gryme", starttime=self.start, venue=self.venue, source=source,
            external_id=external_id, is_approved=False,
        )
        values.update(fields)
        event = Event.all_objects.create(**values)
        # created_at is set on save, so backdate it afterwards to order the copies
        Event.all_objects.filter(pk=event.pk).update(
            created_at=self.created + datetime.timedelta(days=age_days)
        )
        return event

    def fetched_from(self, source):
        VenueFetchStatus.objects.create(venue=self.venue, fetched_at=timezone.now(), source=source)

    def dedupe(self, *args):
        out = StringIO()
        call_command("dedupe_events", *args, stdout=out, no_color=True)
        return out.getvalue()

    def remaining(self):
        return list(Event.all_objects.order_by("pk"))

    def test_eventbrite_and_scraped_copies(self):
        self.fetched_from("eventbrite")
        scraped = self.copy("json-ld:7c91", "ticketing", is_approved=True, kind="dj_dance")
        api = self.copy("eventbrite:1998699082760", "eventbrite", age_days=1, title="GRYME!", kind="live_music")
        self.dedupe()
        [kept] = self.remaining()
        self.assertEqual(kept.pk, api.pk)
        self.assertTrue(kept.is_approved)
        self.assertFalse(Event.all_objects.filter(pk=scraped.pk).exists())
        self.assertEqual(dict(JobRun.objects.get().summary)["copies deleted"], 1)

    def test_equal_copies(self):
        self.fetched_from("ical")
        older = self.copy("ai:365932a4", "ai")
        self.copy("ai:7e03e1b9", "ai", age_days=1)
        self.copy("ai:0081", "ai", age_days=2, is_approved=True)
        self.dedupe()
        [kept] = self.remaining()
        self.assertEqual(kept.pk, older.pk)
        self.assertTrue(kept.is_approved)

    def test_admin_label_carried_over(self):
        self.fetched_from("eventbrite")
        self.copy("json-ld:7c91", "ticketing", kind="dj_dance", kind_set_by=Event.KindSetBy.ADMIN)
        self.copy("eventbrite:1998699082760", "eventbrite", age_days=1, kind="live_music", kind_set_by=Event.KindSetBy.AI)
        self.dedupe()
        [kept] = self.remaining()
        self.assertEqual((kept.source, kept.kind, kept.kind_set_by), ("eventbrite", "dj_dance", Event.KindSetBy.ADMIN))

    def test_kept_copys_own_admin_label_stands(self):
        self.fetched_from("eventbrite")
        self.copy("json-ld:7c91", "ticketing", kind="dj_dance", kind_set_by=Event.KindSetBy.ADMIN)
        self.copy("eventbrite:1", "eventbrite", age_days=1, kind="live_music", kind_set_by=Event.KindSetBy.ADMIN)
        self.dedupe()
        self.assertEqual(self.remaining()[0].kind, "live_music")

    def test_dry_run(self):
        self.fetched_from("eventbrite")
        self.copy("json-ld:7c91", "ticketing", is_approved=True)
        self.copy("eventbrite:1998699082760", "eventbrite", age_days=1)
        output = self.dedupe("--dry-run")
        self.assertEqual(len(self.remaining()), 2)
        self.assertFalse(any(event.is_approved and event.source == "eventbrite" for event in self.remaining()))
        self.assertIn("Arch Street Tavern", output)
        self.assertIn("keep    #", output)
        self.assertIn("eventbrite eventbrite:1998699082760", output)
        self.assertIn("delete  #", output)
        self.assertIn("then    is_approved = True", output)
        self.assertIn("[dry run] would delete 1 copies of 1 shows", output)

    def test_leaves_other_events_alone(self):
        self.copy("ical:a", "ical")
        self.copy("ical:b", "ical", title="Another Show")
        self.copy("ical:c", "ical", starttime=self.start + datetime.timedelta(hours=2))
        self.copy("ical:past", "ical", starttime=timezone.now() - datetime.timedelta(days=1))
        self.copy("ical:past2", "ical", starttime=timezone.now() - datetime.timedelta(days=1))
        # entered by hand: never merged or deleted
        self.copy(None, "")
        self.dedupe()
        self.assertEqual(len(self.remaining()), 6)
