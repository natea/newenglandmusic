from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import DigestChoice, SignInCode, Subscriber, Venue


class SubscriberModelTestCase(TestCase):
    def test_email_is_stored_lowercase_and_unique(self):
        Subscriber.objects.create(email="Fan@Example.COM ")
        self.assertEqual(Subscriber.objects.get().email, "fan@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subscriber.objects.create(email="FAN@example.com")

    def test_deleting_a_subscriber_deletes_choices_and_codes(self):
        subscriber = Subscriber.objects.create(email="a@example.com")
        DigestChoice.objects.create(subscriber=subscriber, kind="area", area_query="all=1")
        SignInCode.objects.create(subscriber=subscriber, code_hash="x")
        subscriber.delete()
        self.assertEqual(DigestChoice.objects.count(), 0)
        self.assertEqual(SignInCode.objects.count(), 0)

    def test_deleting_a_venue_drops_its_choice_only(self):
        subscriber = Subscriber.objects.create(email="a@example.com")
        venue = Venue.objects.create(name="Gone Hall")
        DigestChoice.objects.create(subscriber=subscriber, kind="venue", venue=venue)
        DigestChoice.objects.create(subscriber=subscriber, kind="area", area_query="all=1")
        venue.delete()
        self.assertEqual(list(subscriber.choices.values_list("kind", flat=True)), ["area"])


class SubscriberAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("ed", password="pw"))

    def test_list_shows_address_confirmed_paused_and_created(self):
        Subscriber.objects.create(email="a@example.com", paused=True)
        response = self.client.get("/admin/core/subscriber/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["cl"].list_display, ["action_checkbox", "email", "is_confirmed", "paused", "created_at"]
        )
        self.assertContains(response, "a@example.com")

    def test_choices_are_inline_and_a_subscriber_can_be_deleted(self):
        subscriber = Subscriber.objects.create(email="a@example.com")
        DigestChoice.objects.create(subscriber=subscriber, kind="area", area_query="all=1")
        url = f"/admin/core/subscriber/{subscriber.pk}/change/"
        self.assertContains(self.client.get(url), "choices-0-area_query")
        self.client.post(f"/admin/core/subscriber/{subscriber.pk}/delete/", {"post": "yes"})
        self.assertFalse(Subscriber.objects.exists())
