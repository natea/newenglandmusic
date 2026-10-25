from io import StringIO

from core.models import Event
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone


class ResaveAllEventsTestCase(TestCase):
    def test_unapproved_events_are_rebaked_too(self):
        approved = Event.objects.create(title="approved", starttime=timezone.now())
        pending = Event.objects.create(title="pending", starttime=timezone.now(), is_approved=False)
        Event.all_objects.update(baked_html_template="stale")

        call_command("resave_all_events", stdout=StringIO(), stderr=StringIO())

        for event in (approved, pending):
            html = Event.all_objects.get(pk=event.pk).baked_html_template
            self.assertNotEqual(html, "stale", event.title)
            self.assertIn(event.title, html)
