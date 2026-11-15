from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from core import digest_tokens
from core.models import DigestChoice, MenuItem, SignInCode, Subscriber, Venue

from .digest_fixture import DigestTestCase

ADDRESS = "fan@example.com"


class PreferencesTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.venue = Venue.objects.create(name="The Sinclair", state="MA", city_town="Cambridge")
        self.subscriber = Subscriber.objects.create(email=ADDRESS, confirmed_at=timezone.now())
        DigestChoice.objects.create(subscriber=self.subscriber, kind="area", area_query="state=vermont")
        self.sign_in()

    def sign_in(self, client=None, subscriber=None):
        client = client or self.client
        session = client.session
        session["subscriber_id"] = (subscriber or self.subscriber).pk
        session.save()
        client.cookies["sessionid"] = session.session_key
        return client

    def post(self, data, client=None, **extra):
        return (client or self.client).post("/digest/preferences", data, **extra)

    def test_preferences_page_and_signing_in_lands_there(self):
        response = self.client.get("/digest/preferences")
        self.assertContains(response, ADDRESS)
        self.assertContains(response, 'value="state:vermont" checked')

    def test_sign_in_with_a_code_shows_the_preferences(self):
        client = Client()
        code = digest_tokens.issue_code(self.subscriber)
        response = client.post("/digest/sign-in", {"email": ADDRESS, "code": code}, follow=True)
        self.assertContains(response, "Your shows")

    def test_change_choices(self):
        response = self.post({"area": [], "venue": ["The Sinclair"]})
        self.assertContains(response, "Saved.")
        choices = list(self.subscriber.choices.all())
        self.assertEqual([(c.kind, c.venue) for c in choices], [("venue", self.venue)])

    def test_changing_needs_a_valid_choice_and_keeps_the_old_ones(self):
        response = self.post({"area": []})
        self.assertContains(response, "Choose at least one")
        self.assertEqual(self.subscriber.choices.count(), 1)

    def test_pause_and_resume(self):
        self.post({"action": "pause"})
        self.subscriber.refresh_from_db()
        self.assertTrue(self.subscriber.paused)
        self.assertContains(self.client.get("/digest/preferences"), "Resume the email")
        self.post({"action": "resume"})
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.paused)

    def test_delete_account_with_confirmation(self):
        confirm = self.client.get("/digest/delete")
        self.assertContains(confirm, "can't be undone")
        self.assertTrue(Subscriber.objects.exists())
        digest_tokens.issue_code(self.subscriber)
        self.client.post("/digest/delete")
        self.assertFalse(Subscriber.objects.exists())
        self.assertFalse(DigestChoice.objects.exists())
        self.assertFalse(SignInCode.objects.exists())
        self.assertRedirects(self.client.get("/digest/preferences"), "/digest/sign-in", fetch_redirect_response=False)

    def test_not_signed_in(self):
        self.assertRedirects(Client().get("/digest/preferences"), "/digest/sign-in", fetch_redirect_response=False)
        self.assertRedirects(Client().get("/digest/delete"), "/digest/sign-in", fetch_redirect_response=False)

    def test_not_signed_in_posts_change_nothing(self):
        stranger = Client()
        stranger.post("/digest/preferences", {"action": "pause"})
        stranger.post("/digest/delete")
        stranger.post("/digest/preferences", {"area": ["all"]})
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.paused)
        self.assertEqual(list(self.subscriber.choices.values_list("area_query", flat=True)), ["state=vermont"])

    def test_sign_out(self):
        self.client.post("/digest/sign-out")
        self.assertRedirects(self.client.get("/digest/preferences"), "/digest/sign-in", fetch_redirect_response=False)
        self.assertNotIn("subscriber_id", self.client.session)

    def test_deleted_subscribers_other_browser_is_signed_out(self):
        other = self.sign_in(Client())
        self.assertEqual(other.get("/digest/preferences").status_code, 200)
        self.subscriber.delete()
        self.assertRedirects(other.get("/digest/preferences"), "/digest/sign-in", fetch_redirect_response=False)

    def test_missing_csrf_token(self):
        client = self.sign_in(Client(enforce_csrf_checks=True))
        for url, data in (("/digest/preferences", {"action": "pause"}), ("/digest/delete", {}), ("/digest/sign-out", {})):
            self.assertEqual(client.post(url, data).status_code, 403, url)
        self.subscriber.refresh_from_db()
        self.assertFalse(self.subscriber.paused)
        self.assertTrue(Subscriber.objects.exists())

    def test_page_headers(self):
        for url in ("/digest/preferences", "/digest/delete"):
            response = self.client.get(url)
            self.assertIn("noindex", response["X-Robots-Tag"])
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Referrer-Policy"], "no-referrer")

    def test_area_no_longer_listed(self):
        self.subscriber.choices.update(area_query="state=atlantis")
        response = self.client.get("/digest/preferences")
        self.assertContains(response, "atlantis <b>(no longer listed)</b>", html=False)

    def test_area_partly_gone(self):
        self.subscriber.choices.update(
            area_query="metro=ma-boston-metro-region&town=Somerville%2C+MA&town=Renamedville%2C+MA"
        )
        self.assertContains(self.client.get("/digest/preferences"), "(no longer listed)")

    def test_a_listed_area_is_not_marked(self):
        self.assertNotContains(self.client.get("/digest/preferences"), "no longer listed")


class UnsubscribeTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.subscriber = Subscriber.objects.create(email=ADDRESS, confirmed_at=timezone.now())
        self.url = f"/digest/unsubscribe/{digest_tokens.unsubscribe_token(self.subscriber)}"

    def paused(self):
        return Subscriber.objects.get().paused

    def test_link_then_button(self):
        page = self.client.get(self.url)
        self.assertContains(page, "f***@example.com")
        self.assertNotContains(page, ADDRESS)
        self.assertFalse(self.paused())
        done = self.client.post(self.url)
        self.assertTrue(self.paused())
        self.assertContains(done, "paused")
        self.assertContains(done, "Resume")
        self.assertNotIn("subscriber_id", self.client.session)

    def test_opening_alone_changes_nothing(self):
        self.client.get(self.url)
        self.client.head(self.url)
        self.assertFalse(self.paused())

    def test_one_click_post_without_a_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, {"List-Unsubscribe": "One-Click"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.paused())

    def test_altered_link(self):
        bad = self.url[:-1] + ("a" if self.url[-1] != "a" else "b")
        self.assertEqual(self.client.post(bad).status_code, 400)
        self.assertEqual(self.client.get(bad).status_code, 400)
        self.assertFalse(self.paused())

    def test_a_confirmation_link_is_not_an_unsubscribe_link(self):
        wrong = f"/digest/unsubscribe/{digest_tokens.confirm_token(self.subscriber)}"
        self.assertEqual(self.client.post(wrong).status_code, 400)
        self.assertFalse(self.paused())

    def test_a_deleted_subscribers_link_does_nothing(self):
        self.subscriber.delete()
        self.assertEqual(self.client.post(self.url).status_code, 400)

    def test_resume_after_signing_in(self):
        self.client.post(self.url)
        session = self.client.session
        session["subscriber_id"] = self.subscriber.pk
        session.save()
        self.client.post("/digest/preferences", {"action": "resume"})
        self.assertFalse(self.paused())


class PrivacyAndAdminTestCase(DigestTestCase):
    def test_privacy_page(self):
        html = self.client.get("/privacy").content.decode()
        for text in ("email address", "choices", "rounded", "Amazon SES", "not tracked", "Delete my account"):
            self.assertIn(text, html.replace("Opens and clicks are not tracked", "not tracked"))
        self.assertNotIn("has no accounts", html)
        self.assertNotIn("The only thing it keeps about you", html)

    def test_footer_link(self):
        self.assertTrue(MenuItem.objects.filter(url="/digest", show_in_footer=True).exists())
        self.assertContains(self.client.get("/privacy"), '<a href="/digest">Weekly email</a>')

    def test_admin_lists_subscribers(self):
        Subscriber.objects.create(email=ADDRESS, confirmed_at=timezone.now(), paused=True)
        self.client.force_login(User.objects.create_superuser("ed", password="pw"))
        response = self.client.get("/admin/core/subscriber/")
        self.assertContains(response, ADDRESS)
        for column in ("column-email", "column-is_confirmed", "column-paused", "column-created_at"):
            self.assertContains(response, column)
