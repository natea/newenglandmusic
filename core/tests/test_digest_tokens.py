import datetime
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from core import digest_tokens as tokens
from core.models import MailRequest, SignInCode, Subscriber

START = datetime.datetime(2026, 11, 2, 12, 0, tzinfo=datetime.timezone.utc)


class Clock:
    def __init__(self):
        self.now = START

    def advance(self, **kwargs):
        self.now += datetime.timedelta(**kwargs)

    def __call__(self):
        return self.now


class TokenTestCase(TestCase):
    def setUp(self):
        self.clock = Clock()
        patcher = mock.patch("django.utils.timezone.now", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.subscriber = Subscriber.objects.create(email="fan@example.com")

    def test_valid_link(self):
        token = tokens.confirm_token(self.subscriber)
        self.assertEqual(tokens.subscriber_from(token, tokens.CONFIRM_SALT, tokens.CONFIRM_MAX_AGE), self.subscriber)

    def test_altered_link(self):
        token = tokens.confirm_token(self.subscriber)
        self.assertIsNone(tokens.subscriber_from(token[:-1] + ("a" if token[-1] != "a" else "b"), tokens.CONFIRM_SALT))
        self.assertIsNone(tokens.subscriber_from("", tokens.CONFIRM_SALT))

    def test_a_link_works_only_for_its_purpose(self):
        token = tokens.unsubscribe_token(self.subscriber)
        self.assertIsNone(tokens.subscriber_from(token, tokens.CONFIRM_SALT))

    def test_confirmation_expires_after_seven_days_and_unsubscribe_never_does(self):
        confirm, unsubscribe = tokens.confirm_token(self.subscriber), tokens.unsubscribe_token(self.subscriber)
        self.clock.advance(days=7, minutes=-1)
        self.assertTrue(tokens.subscriber_from(confirm, tokens.CONFIRM_SALT, tokens.CONFIRM_MAX_AGE))
        self.clock.advance(minutes=2)
        self.assertIsNone(tokens.subscriber_from(confirm, tokens.CONFIRM_SALT, tokens.CONFIRM_MAX_AGE))
        self.clock.advance(days=900)
        self.assertEqual(tokens.subscriber_from(unsubscribe, tokens.UNSUBSCRIBE_SALT), self.subscriber)

    def test_a_deleted_subscribers_links_do_nothing(self):
        token = tokens.unsubscribe_token(self.subscriber)
        self.subscriber.delete()
        self.assertIsNone(tokens.subscriber_from(token, tokens.UNSUBSCRIBE_SALT))


class CodeTestCase(TestCase):
    def setUp(self):
        self.clock = Clock()
        patcher = mock.patch("django.utils.timezone.now", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.subscriber = Subscriber.objects.create(email="fan@example.com")

    def test_code_is_six_digits_and_only_a_hash_is_stored(self):
        code = tokens.issue_code(self.subscriber)
        self.assertRegex(code, r"^\d{6}$")
        stored = SignInCode.objects.get()
        self.assertNotIn(code, stored.code_hash)
        self.assertEqual(len(stored.code_hash), 64)

    def test_correct_code_works_once(self):
        code = tokens.issue_code(self.subscriber)
        self.assertTrue(tokens.check_code(self.subscriber, code))
        self.assertFalse(tokens.check_code(self.subscriber, code))

    def test_newer_code_cancels_older(self):
        first = tokens.issue_code(self.subscriber)
        second = tokens.issue_code(self.subscriber)
        if first == second:
            self.skipTest("the two random codes matched")
        self.assertFalse(tokens.check_code(self.subscriber, first))
        self.assertTrue(tokens.check_code(self.subscriber, second))

    def test_expires_after_fifteen_minutes(self):
        code = tokens.issue_code(self.subscriber)
        self.clock.advance(minutes=16)
        self.assertFalse(tokens.check_code(self.subscriber, code))

    def test_still_works_at_fourteen_minutes(self):
        code = tokens.issue_code(self.subscriber)
        self.clock.advance(minutes=14)
        self.assertTrue(tokens.check_code(self.subscriber, code))

    def test_five_wrong_tries_lock_the_code(self):
        code = tokens.issue_code(self.subscriber)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertFalse(tokens.check_code(self.subscriber, wrong))
        self.assertFalse(tokens.check_code(self.subscriber, code))
        fresh = tokens.issue_code(self.subscriber)
        self.assertTrue(tokens.check_code(self.subscriber, fresh))

    def test_ten_wrong_tries_an_hour_lock_the_address(self):
        wrong = "abcdef"
        for _ in range(2):
            code = tokens.issue_code(self.subscriber)
            for _ in range(5):
                tokens.check_code(self.subscriber, wrong)
        code = tokens.issue_code(self.subscriber)
        self.assertFalse(tokens.check_code(self.subscriber, code))
        self.clock.advance(minutes=61)
        code = tokens.issue_code(self.subscriber)
        self.assertTrue(tokens.check_code(self.subscriber, code))


class LimitTestCase(TestCase):
    def setUp(self):
        self.clock = Clock()
        patcher = mock.patch("django.utils.timezone.now", self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_three_emails_an_hour_to_one_address(self):
        results = [tokens.may_send_mail("Fan@example.com") for _ in range(4)]
        self.assertEqual(results, [True, True, True, False])
        self.assertTrue(tokens.may_send_mail("other@example.com"))
        self.clock.advance(minutes=61)
        self.assertTrue(tokens.may_send_mail("fan@example.com"))

    def test_ten_requests_an_hour_from_one_client(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1")
        limited = [tokens.client_limited(request) for _ in range(11)]
        self.assertEqual(limited, [False] * 10 + [True])
        other = RequestFactory().get("/", REMOTE_ADDR="10.0.0.2")
        self.assertFalse(tokens.client_limited(other))

    def test_client_address_is_the_last_forwarded_entry(self):
        factory = RequestFactory()
        single = factory.get("/", HTTP_X_FORWARDED_FOR="203.0.113.9", REMOTE_ADDR="10.0.0.1")
        multi = factory.get("/", HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9", REMOTE_ADDR="10.0.0.1")
        none = factory.get("/", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(tokens.client_address(single), "203.0.113.9")
        self.assertEqual(tokens.client_address(multi), "203.0.113.9")
        self.assertEqual(tokens.client_address(none), "10.0.0.1")
        self.assertEqual(tokens.client_hash(single), tokens.client_hash(multi))
        self.assertNotIn("203.0.113.9", tokens.client_hash(single))

    def test_old_requests_are_deleted_after_a_day(self):
        tokens.may_send_mail("fan@example.com")
        self.clock.advance(hours=25)
        tokens.may_send_mail("new@example.com")
        self.assertEqual(tokens.delete_old_requests(), 1)
        self.assertEqual(MailRequest.objects.count(), 1)


class AfterResponseTestCase(TestCase):
    def test_send_runs_only_when_the_response_is_closed(self):
        sent = []
        response = tokens.send_after_response(HttpResponse("ok"), lambda: sent.append(1))
        self.assertEqual(sent, [])
        response.close()
        self.assertEqual(sent, [1])
