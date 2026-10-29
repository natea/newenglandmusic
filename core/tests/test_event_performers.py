import datetime

from core.event_performers import link_from_names, names_to_records
from core.management.commands import fetch_events
from core.models import Artist, Band, Event, EventPerformer, Venue
from core.tests.test_fetch_events import event as event_data
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone


def performers(event):
    return [(p.act.name, p.source) for p in event.performers.select_related("artist", "band").order_by("order", "pk")]


class EventPerformerModelTestCase(TestCase):
    def setUp(self):
        self.event = Event.all_objects.create(title="show", starttime=timezone.now())
        self.band = Band.objects.create(name="Pixies")
        self.artist = Artist.objects.create(name="Kim Deal")

    def test_an_artist_or_a_band(self):
        for fields in ({}, {"artist": self.artist, "band": self.band}):
            with self.subTest(fields=fields), self.assertRaises(IntegrityError), transaction.atomic():
                EventPerformer.objects.create(event=self.event, **fields)

    def test_no_performer_twice(self):
        EventPerformer.objects.create(event=self.event, band=self.band)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EventPerformer.objects.create(event=self.event, band=self.band, order=1)
        # an artist and a band are separate performers
        EventPerformer.objects.create(event=self.event, artist=self.artist, order=1)


class LinkFromNamesTestCase(TestCase):
    def setUp(self):
        self.pixies = Band.objects.create(name="Pixies")
        self.speedy = Band.objects.create(name="Speedy Ortiz")
        self.kim = Artist.objects.create(name="Kim Deal")
        self.pile = Band.objects.create(name="Pile")

    def event(self, artists):
        return Event.all_objects.create(title="show", artists=artists, starttime=timezone.now())

    def test_several_acts_on_one_bill(self):
        event = self.event("Pixies, Speedy Ortiz, Kim Deal")
        link_from_names(event)
        self.assertEqual(performers(event), [("Pixies", "names"), ("Speedy Ortiz", "names"), ("Kim Deal", "names")])

    def test_a_name_with_no_record(self):
        event = self.event("Pixies, Dana and Alden, TBA")
        link_from_names(event)
        self.assertEqual(performers(event), [("Pixies", "names")])
        self.assertEqual(Event.all_objects.get(pk=event.pk).artists, "Pixies, Dana and Alden, TBA")

    def test_two_records_with_one_name(self):
        Artist.objects.create(name="Horse")
        Band.objects.create(name="Horse")
        event = self.event("Horse, Pixies")
        link_from_names(event)
        self.assertEqual(performers(event), [("Pixies", "names")])
        self.assertNotIn("horse", names_to_records())

    def test_names_compared_normalized_and_once(self):
        event = self.event("the pixies, PIXIES (DJ Set), Kim Deal")
        link_from_names(event)
        self.assertEqual(performers(event), [("Pixies", "names"), ("Kim Deal", "names")])

    def test_the_text_changes(self):
        event = self.event("Pixies, Speedy Ortiz")
        link_from_names(event)
        event.artists = "Pixies, Pile"
        link_from_names(event)
        self.assertEqual(performers(event), [("Pixies", "names"), ("Pile", "names")])

    def test_an_editors_performer_stays(self):
        lsd = Band.objects.create(name="Lake Street Dive")
        event = self.event("Pixies")
        EventPerformer.objects.create(event=event, band=lsd, order=5, source="editor")
        EventPerformer.objects.create(event=event, band=self.pixies, order=0, source="editor")
        link_from_names(event)
        # the editor's pixies isn't added again from the name
        self.assertEqual(performers(event), [("Pixies", "editor"), ("Lake Street Dive", "editor")])


class FetchedEventsAreLinkedTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V0001", name="Venue", state="MA")
        self.pixies = Band.objects.create(name="Pixies")

    def test_a_saved_event_is_linked(self):
        fetch_events.save_event(self.venue.pk, "ical", "", event_data("Show", artists="Pixies, Nobody"), dry_run=False)
        self.assertEqual(performers(Event.all_objects.get()), [("Pixies", "names")])

    def test_an_updated_event_is_relinked(self):
        Band.objects.create(name="Krill")
        fetch_events.save_event(self.venue.pk, "ical", "", event_data("Show", artists="Pixies"), dry_run=False)
        fetch_events.save_event(self.venue.pk, "ical", "", event_data("Show", artists="Krill"), dry_run=False)
        self.assertEqual(performers(Event.all_objects.get()), [("Krill", "names")])

    def test_not_in_a_dry_run(self):
        fetch_events.save_event(self.venue.pk, "ical", "", event_data("Show", artists="Pixies"), dry_run=True)
        self.assertEqual(EventPerformer.objects.count(), 0)


class EventPerformerAdminTestCase(TestCase):
    """the event admin's performers inline: add, reorder and remove"""

    def setUp(self):
        from core.admin import EventAdmin
        from django.contrib.admin.sites import AdminSite
        from django.contrib.auth.models import User
        from django.test import RequestFactory

        self.admin = EventAdmin(Event, AdminSite())
        self.request = RequestFactory().post("/")
        self.request.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.event = Event.all_objects.create(title="show", artists="Pixies", starttime=timezone.now())
        self.pixies = Band.objects.create(name="Pixies")
        self.lsd = Band.objects.create(name="Lake Street Dive")
        self.kim = Artist.objects.create(name="Kim Deal")
        link_from_names(self.event)

    def save(self, rows):
        inline = self.admin.get_inline_instances(self.request, self.event)[0]
        FormSet = inline.get_formset(self.request, self.event)
        existing = list(self.event.performers.order_by("order", "pk"))
        data = {"performers-TOTAL_FORMS": str(len(rows)), "performers-INITIAL_FORMS": str(len(existing)),
                "performers-MIN_NUM_FORMS": "0", "performers-MAX_NUM_FORMS": "1000"}
        for i, row in enumerate(rows):
            for key, value in row.items():
                data[f"performers-{i}-{key}"] = "" if value is None else str(value)
            data[f"performers-{i}-event"] = str(self.event.pk)
        formset = FormSet(data, instance=self.event, prefix="performers")
        self.assertTrue(formset.is_valid(), formset.errors)
        self.admin.save_formset(self.request, None, formset, True)

    def test_add_reorder_and_remove(self):
        pixies = self.event.performers.get()
        self.save([
            {"id": pixies.pk, "order": 2, "band": self.pixies.pk},
            {"order": 0, "band": self.lsd.pk},
            {"order": 1, "artist": self.kim.pk},
        ])
        self.assertEqual(performers(self.event), [("Lake Street Dive", "editor"), ("Kim Deal", "editor"), ("Pixies", "editor")])
        # removing one
        rows = [{"id": p.pk, "order": p.order, "artist": p.artist_id, "band": p.band_id} for p in self.event.performers.order_by("order")]
        rows[1]["DELETE"] = "on"
        self.save(rows)
        self.assertEqual([name for name, _ in performers(self.event)], ["Lake Street Dive", "Pixies"])

    def test_an_editors_performer_survives_relinking(self):
        self.save([{"id": self.event.performers.get().pk, "order": 0, "band": self.pixies.pk}, {"order": 1, "band": self.lsd.pk}])
        link_from_names(self.event)
        # pixies, untouched, is still linked from the text; the editor's addition stays
        self.assertEqual(performers(self.event), [("Pixies", "names"), ("Lake Street Dive", "editor")])

    def test_the_inline_is_on_the_event_page(self):
        self.client.force_login(self.request.user)
        from django.urls import reverse

        html = self.client.get(reverse("admin:core_alleventproxy_change", args=[self.event.pk])).content.decode()
        self.assertIn("performers-TOTAL_FORMS", html)
        self.assertIn("take the name out to unlink it", html)
