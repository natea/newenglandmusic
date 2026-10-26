from core.admin import EventAdmin
from core.models import AllEventProxy, Event
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone


class EventAdminKindTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.admin = EventAdmin(AllEventProxy, AdminSite())
        self.events = {
            kind or "unlabelled": Event.objects.create(
                title=f"{kind or 'unlabelled'} event",
                starttime=timezone.now() + timezone.timedelta(days=3),
                kind=kind,
                is_approved=False,
            )
            for kind in ("", "live_music", "dj_dance", "open_mic", "karaoke", "comedy", "other")
        }

    def listed(self, **params):
        request = RequestFactory().get("/admin/core/alleventproxy/", params)
        request.user = self.user
        changelist = self.admin.get_changelist_instance(request)
        return {e.title.removesuffix(" event") for e in changelist.get_queryset(request)}

    def test_default_list_shows_music_and_unlabelled(self):
        self.assertEqual(self.listed(), {"unlabelled", "live_music", "dj_dance", "open_mic"})

    def test_filter_options(self):
        self.assertEqual(self.listed(kind="not_music"), {"karaoke", "comedy", "other"})
        self.assertEqual(self.listed(kind="comedy"), {"comedy"})
        self.assertEqual(self.listed(kind="unlabelled"), {"unlabelled"})
        self.assertEqual(len(self.listed(kind="all")), 7)

    def test_kind_column_and_form_field(self):
        self.assertIn("kind", self.admin.list_display)
        self.assertIn("kind", self.admin.fields)

    def test_labelling_never_changes_approval(self):
        approved = Event.objects.create(
            title="approved comedy", starttime=timezone.now(), kind="comedy", is_approved=True
        )
        # still on the site
        self.assertTrue(Event.objects.filter(pk=approved.pk).exists())

    def run_action(self, action, *kinds):
        request = RequestFactory().post("/admin/core/alleventproxy/")
        request.user = self.user
        queryset = AllEventProxy.objects.filter(pk__in=[self.events[k].pk for k in kinds])
        getattr(self.admin, action)(request, queryset)

    def test_mark_as_live_music(self):
        self.run_action("mark_as_live_music", "other", "comedy")
        for key in ("other", "comedy"):
            event = Event.all_objects.get(pk=self.events[key].pk)
            self.assertEqual((event.kind, event.kind_set_by), ("live_music", "admin"))
        self.assertIn("comedy event", {e.title for e in Event.all_objects.filter(kind="live_music")})

    def test_mark_as_unapproved(self):
        Event.all_objects.filter(pk__in=[self.events["comedy"].pk, self.events["other"].pk]).update(is_approved=True)
        self.run_action("mark_as_unapproved", "comedy")
        self.assertFalse(Event.all_objects.get(pk=self.events["comedy"].pk).is_approved)
        # off the site, and its label unchanged
        self.assertFalse(Event.objects.filter(pk=self.events["comedy"].pk).exists())
        self.assertEqual(Event.all_objects.get(pk=self.events["comedy"].pk).kind, "comedy")
        self.assertTrue(Event.all_objects.get(pk=self.events["other"].pk).is_approved)
        self.assertIn("mark_as_unapproved", self.admin.actions)

    def test_mark_as_not_music(self):
        self.run_action("mark_as_not_music", "live_music")
        event = Event.all_objects.get(pk=self.events["live_music"].pk)
        self.assertEqual((event.kind, event.kind_set_by), ("other", "admin"))

    def test_kind_chosen_in_the_form_is_an_admin_label(self):
        event = AllEventProxy.objects.get(pk=self.events["other"].pk)
        request = RequestFactory().post("/")
        request.user = self.user
        form = mock_form(changed=["kind"])
        event.kind = "live_music"
        self.admin.save_model(request, event, form, change=True)
        event = Event.all_objects.get(pk=event.pk)
        self.assertEqual((event.kind, event.kind_set_by), ("live_music", "admin"))

        # clearing it in the form hands it back to the labeller
        event = AllEventProxy.objects.get(pk=event.pk)
        event.kind = ""
        self.admin.save_model(request, event, mock_form(changed=["kind"]), change=True)
        self.assertEqual(Event.all_objects.get(pk=event.pk).kind_set_by, "")


def mock_form(changed):
    class Form:
        changed_data = changed

    return Form()
