from datetime import timedelta
from unittest import mock

from django.test import Client
from django.utils import timezone

from core.models import SignInCode, Subscriber

from .digest_fixture import DigestTestCase, body

ADDRESS = "fan@example.com"


class SignInTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.subscriber = Subscriber.objects.create(email=ADDRESS, confirmed_at=timezone.now())

    def ask(self, address=ADDRESS, client=None):
        return (client or self.client).post("/digest/sign-in", {"email": address})

    def enter(self, code, address=ADDRESS, client=None):
        return (client or self.client).post("/digest/sign-in", {"email": address, "code": code})

    def last_code(self):
        import re

        return re.search(r"code is (\d{6})", body(self.messages()[-1]))[1]

    def test_correct_code_signs_in(self):
        self.ask()
        response = self.enter(self.last_code())
        self.assertRedirects(response, "/digest/preferences", fetch_redirect_response=False)
        self.assertEqual(self.client.session["subscriber_id"], self.subscriber.pk)

    def test_code_email_holds_only_the_code_and_no_link_or_unsubscribe_headers(self):
        self.ask()
        message = self.messages()[0]
        self.assertRegex(body(message), r"code is \d{6}")
        self.assertNotIn("http", body(message))
        self.assertNotIn("List-Unsubscribe", message)
        self.assertEqual(message.get_content_type(), "multipart/alternative")

    def test_session_key_changes_and_no_django_user_is_logged_in(self):
        self.client.get("/digest/sign-in")
        before = self.client.session.session_key
        self.ask()
        self.enter(self.last_code())
        self.assertNotEqual(self.client.session.session_key, before)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session.get_expiry_age(), 30 * 24 * 60 * 60)

    def test_only_a_keyed_hash_is_stored(self):
        self.ask()
        self.assertNotIn(self.last_code(), SignInCode.objects.get().code_hash)

    def test_newer_code_cancels_older(self):
        self.ask()
        first = self.last_code()
        self.ask()
        second = self.last_code()
        if first != second:
            self.assertContains(self.enter(first), "didn&#x27;t work")
        self.assertEqual(self.enter(second).status_code, 302)

    def test_code_used_twice(self):
        self.ask()
        code = self.last_code()
        self.enter(code)
        self.assertContains(self.enter(code, client=Client()), "didn&#x27;t work")

    def test_expired_code_offers_a_new_one(self):
        self.ask()
        code = self.last_code()
        later = timezone.now() + timedelta(minutes=16)
        with mock.patch("django.utils.timezone.now", lambda: later):
            response = self.enter(code)
        self.assertContains(response, "Send a new one")
        self.assertNotIn("subscriber_id", self.client.session)

    def test_five_wrong_tries_lock_the_code(self):
        self.ask()
        code = self.last_code()
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.enter(wrong)
        self.assertContains(self.enter(code), "didn&#x27;t work")

    def test_ten_wrong_tries_for_one_address_across_requests(self):
        for _ in range(2):
            self.ask()
            for _ in range(5):
                self.enter("abcdef")
        # eleven client requests would be limited first, so use another client for the last
        fresh = Client()
        self.ask(client=fresh)
        self.assertContains(self.enter(self.last_code(), client=fresh), "didn&#x27;t work")

    def test_unknown_address_looks_the_same_and_sends_nothing(self):
        known = self.ask()
        unknown = self.ask("nobody@example.com", client=Client())
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertContains(unknown, "we sent it a 6-digit code")
        self.assertEqual(len(self.ses.sent), 1)

    def test_unconfirmed_address_gets_nothing(self):
        Subscriber.objects.create(email="new@example.com")
        self.ask("new@example.com")
        self.assertEqual(self.ses.sent, [])

    def test_replies_do_not_wait_for_the_mail_service(self):
        seen = []
        original = self.ses.send_raw_email

        def watching(**kwargs):
            seen.append("sent")
            return original(**kwargs)

        self.ses.send_raw_email = watching
        # the client closes the response after the view returns: nothing is sent before that
        with mock.patch("core.views.digest.digest_tokens.send_after_response", side_effect=lambda r, send: r) as later:
            self.ask()
            self.ask("nobody@example.com", client=Client())
        self.assertEqual(seen, [])
        self.assertEqual(later.call_count, 1)
        self.ask(client=Client())
        self.assertEqual(seen, ["sent"])

    def test_address_limit(self):
        for _ in range(4):
            self.ask(client=Client())
        self.assertEqual(len(self.ses.sent), 3)

    def test_client_limit(self):
        for i in range(10):
            self.ask(f"p{i}@example.com")
        self.ses.sent.clear()
        self.ask()
        self.assertEqual(self.ses.sent, [])

    def test_signed_in_visitors_go_to_preferences(self):
        self.ask()
        self.enter(self.last_code())
        self.assertRedirects(self.client.get("/digest/sign-in"), "/digest/preferences", fetch_redirect_response=False)

    def test_csrf_token_is_required(self):
        response = Client(enforce_csrf_checks=True).post("/digest/sign-in", {"email": ADDRESS})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.ses.sent, [])

    def test_a_line_break_in_the_address(self):
        response = self.ask("fan@example.com\nBcc: x@example.com")
        self.assertContains(response, "email address")
        self.assertEqual(self.ses.sent, [])
