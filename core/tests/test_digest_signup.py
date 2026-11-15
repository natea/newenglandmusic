from django.test import Client
from django.utils import timezone

from core import digest_tokens
from core.geo_filters import COOKIE_NAME as GEO_COOKIE
from core.location import COOKIE_NAME as NEAR_COOKIE
from core.location import Location, encode
from core.models import DigestChoice, Subscriber, Venue

from .digest_fixture import DigestTestCase, body

ADDRESS = "fan@example.com"


class SignupTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.venue = Venue.objects.create(name="The Sinclair", state="MA", city_town="Cambridge", county="Middlesex", latitude=42.37, longitude=-71.1)

    def post(self, extra=None, client=None, **headers):
        data = {"email": ADDRESS, "area": ["state:vermont"]}
        data.update(extra or {})
        return (client or self.client).post("/digest", data, **headers)

    def test_form_asks_for_no_password_or_phone(self):
        html = self.client.get("/digest").content.decode()
        self.assertIn('type="email"', html)
        self.assertNotIn("password", html.lower().replace("no password", ""))
        self.assertNotIn('type="tel"', html)

    def test_new_address(self):
        response = self.post()
        self.assertRedirects(response, "/digest/check-email", fetch_redirect_response=False)
        subscriber = Subscriber.objects.get(email=ADDRESS)
        self.assertIsNone(subscriber.confirmed_at)
        self.assertEqual([c.area_query for c in subscriber.choices.all()], ["state=vermont"])
        self.assertEqual(len(self.ses.sent), 1)
        message = self.messages()[0]
        self.assertEqual(message["To"], ADDRESS)
        self.assertIn("/digest/confirm/", body(message))
        self.assertContains(self.client.get("/digest/check-email"), ADDRESS)

    def test_address_is_stored_lowercase(self):
        self.post({"email": " Fan@Example.COM "})
        self.assertTrue(Subscriber.objects.filter(email=ADDRESS).exists())

    def test_confirmation_says_who_asked_and_that_it_can_be_ignored(self):
        self.post()
        text = body(self.messages()[0])
        self.assertIn("Someone asked", text)
        self.assertIn("ignore", text)

    def test_already_signed_up(self):
        subscriber = Subscriber.objects.create(email=ADDRESS, confirmed_at=timezone.now())
        DigestChoice.objects.create(subscriber=subscriber, kind="area", area_query="all=1")
        response = self.post({"area": ["state:vermont"]})
        self.assertRedirects(response, "/digest/check-email", fetch_redirect_response=False)
        self.assertEqual(list(subscriber.choices.values_list("area_query", flat=True)), ["all=1"])
        message = self.messages()[0]
        self.assertIn("already has a subscription", body(message))
        self.assertIn("/digest/sign-in", body(message))
        self.assertNotIn("/digest/confirm/", body(message))

    def test_signing_up_again_before_confirming_keeps_the_choices(self):
        self.post()
        self.post({"area": ["state:massachusetts"]})
        self.assertEqual(Subscriber.objects.count(), 1)
        self.assertEqual([c.area_query for c in Subscriber.objects.get().choices.all()], ["state=vermont"])
        self.assertEqual(len(self.ses.sent), 2)
        self.assertTrue(all("/digest/confirm/" in body(m) for m in self.messages()))

    def test_same_page_for_new_and_known_addresses(self):
        Subscriber.objects.create(email="known@example.com", confirmed_at=timezone.now())
        a = self.post({"email": "new@example.com"}, client=Client())
        b = self.post({"email": "known@example.com"}, client=Client())
        self.assertEqual((a.status_code, a["Location"]), (b.status_code, b["Location"]))
        page_a = Client().get("/digest/check-email").content
        self.assertEqual(page_a, Client().get("/digest/check-email").content)

    def test_not_an_email_address(self):
        response = self.post({"email": "not-an-email"})
        self.assertContains(response, "doesn&#x27;t look like an email address")
        self.assertFalse(Subscriber.objects.exists())
        self.assertEqual(self.ses.sent, [])

    def test_a_line_break_in_the_address(self):
        response = self.post({"email": "fan@example.com\nBcc: other@example.com"})
        self.assertContains(response, "email address")
        self.assertFalse(Subscriber.objects.exists())
        self.assertEqual(self.ses.sent, [])

    def test_no_choice(self):
        response = self.post({"area": []})
        self.assertContains(response, "Choose at least one")
        self.assertFalse(Subscriber.objects.exists())

    def test_several_kinds_together(self):
        self.post({"area": ["state:vermont"], "near_q": "02144", "near_miles": "10", "venue": ["The Sinclair (Cambridge, MA)", ""]})
        kinds = sorted(Subscriber.objects.get().choices.values_list("kind", flat=True))
        self.assertEqual(kinds, ["area", "near", "venue"])

    def test_place_is_stored_rounded(self):
        # 02143 isn't in the fixture; 02144 is, and its census point has six decimal places
        self.post({"area": [], "near_q": "02144", "near_miles": "10"})
        choice = Subscriber.objects.get().choices.get()
        self.assertEqual((choice.label, choice.latitude, choice.longitude, choice.miles), ("02144", 42.4, -71.123, 10))

    def test_unknown_place(self):
        response = self.post({"near_q": "99999", "near_miles": "10"})
        self.assertContains(response, "couldn&#x27;t find")
        self.assertFalse(Subscriber.objects.exists())

    def test_a_shared_town_name_asks_which(self):
        Venue.objects.create(name="Vermont Hall", state="VT", city_town="Springfield")
        Venue.objects.create(name="Bay State Hall", state="MA", city_town="Springfield")
        response = self.post({"area": [], "near_q": "Springfield", "near_miles": "25"})
        self.assertContains(response, "Which “Springfield”")
        self.assertContains(response, "Springfield, VT")
        self.assertFalse(Subscriber.objects.exists())
        picked = self.post({"area": [], "near_q": "Springfield", "near_pick": "Springfield, VT", "near_miles": "25"})
        self.assertEqual(picked.status_code, 302)
        self.assertEqual(Subscriber.objects.get().choices.get().label, "Springfield, VT")

    def test_all_of_the_northeast(self):
        self.post({"area": ["all"]})
        self.assertEqual(list(Subscriber.objects.get().choices.values_list("area_query", flat=True)), ["all=1"])

    def test_followed_town_and_unknown_town(self):
        self.post({"area": [], "town": ["cambridge, ma"]})
        choice = Subscriber.objects.get().choices.get()
        self.assertEqual((choice.kind, choice.town, choice.state), ("town", "Cambridge", "MA"))
        response = self.post({"email": "b@example.com", "area": [], "town": ["Atlantis, ZZ"]})
        self.assertContains(response, "don&#x27;t list a town")

    def test_metro_narrowed_to_towns(self):
        self.post({"area": [], "metro_town": ["ma-north-of-the-charles|Cambridge, MA"]})
        choice = Subscriber.objects.get().choices.get()
        self.assertEqual(choice.area_query, "metro=ma-north-of-the-charles&town=Cambridge%2C+MA")

    def test_an_unoffered_area_is_refused(self):
        response = self.post({"area": ["state:atlantis"]})
        self.assertContains(response, "isn&#x27;t offered")
        self.assertFalse(Subscriber.objects.exists())

    def test_twenty_choices_accepted_and_twenty_one_refused(self):
        for i in range(21):
            Venue.objects.create(name=f"Hall {i}", state="MA", city_town="Boston")
        names = [f"Hall {i}" for i in range(21)]
        self.assertContains(self.post({"area": [], "venue": names}), "Choose at most 20")
        self.assertFalse(Subscriber.objects.exists())
        self.assertEqual(self.post({"area": [], "venue": names[:20]}).status_code, 302)
        self.assertEqual(Subscriber.objects.get().choices.count(), 20)

    def test_form_starts_from_the_remembered_filter_and_location(self):
        self.client.cookies[GEO_COOKIE] = "state=vermont"
        self.client.cookies[NEAR_COOKIE] = encode(Location("02144", 42.4, -71.123))
        response = self.client.get("/digest")
        self.assertContains(response, 'value="state:vermont" checked')
        self.assertContains(response, 'value="02144"')

    def test_remembered_neighborhood_narrowing_is_dropped(self):
        Venue.objects.create(name="Hall", state="MA", city_town="Somerville", neighborhood="Union Square")
        self.client.cookies[GEO_COOKIE] = "metro=ma-north-of-the-charles&town=Somerville%2C+MA&neighborhood=Union+Square%2C+Somerville%2C+MA"
        response = self.client.get("/digest")
        self.assertContains(response, 'value="metro:ma-north-of-the-charles" checked')
        self.assertNotContains(response, "Union Square")
        self.post({"area": ["metro:ma-north-of-the-charles"], "metro_town": ["ma-north-of-the-charles|Somerville, MA"]})
        self.assertNotIn("neighborhood", Subscriber.objects.get().choices.get().area_query)

    def test_address_limit(self):
        for _ in range(4):
            response = self.post()
            self.assertRedirects(response, "/digest/check-email", fetch_redirect_response=False)
        self.assertEqual(len(self.ses.sent), 3)

    def test_client_limit(self):
        for i in range(10):
            self.post({"email": f"p{i}@example.com"})
        self.ses.sent.clear()
        response = self.post({"email": "eleventh@example.com"})
        self.assertRedirects(response, "/digest/check-email", fetch_redirect_response=False)
        self.assertFalse(Subscriber.objects.filter(email="eleventh@example.com").exists())
        self.assertEqual(self.ses.sent, [])

    def test_clients_are_told_apart_by_the_last_forwarded_entry(self):
        for i in range(10):
            self.post({"email": f"p{i}@example.com"}, HTTP_X_FORWARDED_FOR=f"6.6.6.{i}, 203.0.113.9")
        self.post({"email": "late@example.com"}, HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.9")
        self.assertFalse(Subscriber.objects.filter(email="late@example.com").exists())
        self.post({"email": "other@example.com"}, HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.77")
        self.assertTrue(Subscriber.objects.filter(email="other@example.com").exists())

    def test_hidden_field_filled(self):
        response = self.post({"website": "spam"})
        self.assertRedirects(response, "/digest/check-email", fetch_redirect_response=False)
        self.assertFalse(Subscriber.objects.exists())
        self.assertEqual(self.ses.sent, [])

    def test_csrf_token_is_required(self):
        response = Client(enforce_csrf_checks=True).post("/digest", {"email": ADDRESS, "area": ["all"]})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Subscriber.objects.exists())

    def test_a_failed_send_is_logged_without_the_address_and_does_not_break_the_page(self):
        from botocore.exceptions import NoCredentialsError

        self.ses.error = NoCredentialsError()
        with self.assertLogs("core.digest_mail", "ERROR") as logs:
            response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(ADDRESS, "".join(logs.output))

    def test_pages_carry_the_guard_headers(self):
        for url in ("/digest", "/digest/check-email", "/digest/sign-in"):
            response = self.client.get(url)
            self.assertIn("noindex", response["X-Robots-Tag"], url)
            self.assertIn("no-store", response["Cache-Control"], url)
            self.assertEqual(response["Referrer-Policy"], "no-referrer", url)


class ConfirmTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.subscriber = Subscriber.objects.create(email=ADDRESS)
        self.url = f"/digest/confirm/{digest_tokens.confirm_token(self.subscriber)}"

    def test_link_then_button(self):
        page = self.client.get(self.url)
        self.assertContains(page, "Confirm")
        self.assertIsNone(Subscriber.objects.get().confirmed_at)
        self.client.post(self.url)
        self.assertIsNotNone(Subscriber.objects.get().confirmed_at)
        self.assertNotIn("subscriber_id", self.client.session)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_opening_alone_changes_nothing(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertIsNone(Subscriber.objects.get().confirmed_at)

    def test_altered_link(self):
        for method in (self.client.get, self.client.post):
            response = method(self.url[:-1] + ("a" if self.url[-1] != "a" else "b"))
            self.assertContains(response, "Sign up again")
        self.assertIsNone(Subscriber.objects.get().confirmed_at)

    def test_expired_link(self):
        from datetime import timedelta
        from unittest import mock

        later = timezone.now() + timedelta(days=8)
        with mock.patch("django.utils.timezone.now", lambda: later):
            response = self.client.post(self.url)
        self.assertContains(response, "Sign up again")
        self.assertIsNone(Subscriber.objects.get().confirmed_at)

    def test_confirm_post_needs_a_csrf_token(self):
        response = Client(enforce_csrf_checks=True).post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(Subscriber.objects.get().confirmed_at)
