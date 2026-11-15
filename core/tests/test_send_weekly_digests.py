import datetime
import io
from unittest import mock

from botocore.exceptions import ClientError, NoCredentialsError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from core import digest
from core.models import DigestChoice, Event, JobRun, MailRequest, SignInCode, Subscriber, Venue

from .digest_fixture import DigestTestCase, body

THURSDAY = datetime.datetime(2026, 11, 5, 13, 0, tzinfo=datetime.timezone.utc)  # 8 am in New York
MONDAY = datetime.date(2026, 11, 2)


def at(days, hour=20):
    return datetime.datetime.combine(datetime.date(2026, 11, 5) + datetime.timedelta(days=days), datetime.time(hour), tzinfo=digest.NEW_YORK)


class SendTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.now = THURSDAY
        for patcher in (
            mock.patch("django.utils.timezone.now", lambda: self.now),
            mock.patch("core.management.commands.send_weekly_digests.time.sleep"),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.venue = Venue.objects.create(name="The Sinclair", state="MA", city_town="Cambridge")
        Event.objects.create(title="Friday show", starttime=at(1), venue=self.venue)

    def subscriber(self, address="fan@example.com", **fields):
        fields.setdefault("confirmed_at", self.now)
        subscriber = Subscriber.objects.create(email=address, **fields)
        DigestChoice.objects.create(subscriber=subscriber, kind="venue", venue=self.venue)
        return subscriber

    def run_command(self, *args):
        out, err = io.StringIO(), io.StringIO()
        try:
            call_command("send_weekly_digests", *args, stdout=out, stderr=err)
        finally:
            self.output = out.getvalue() + err.getvalue()

    def addresses(self):
        return [message["To"] for message in self.messages()]


class SendingTestCase(SendTestCase):
    def test_a_confirmed_subscriber_with_shows_gets_one_email(self):
        subscriber = self.subscriber()
        self.run_command()
        self.assertEqual(self.addresses(), ["fan@example.com"])
        subscriber.refresh_from_db()
        self.assertEqual(subscriber.last_digest_week, MONDAY)
        self.assertIn("Friday show", body(self.messages()[0]))
        self.assertEqual(self.messages()[0]["From"], "events@digest.example.org")

    def test_recorded_as_a_job_run_with_a_summary(self):
        self.subscriber()
        self.run_command()
        run = JobRun.objects.get(command="send_weekly_digests")
        self.assertEqual(run.status, JobRun.Status.SUCCEEDED)
        self.assertIn(["sent", 1], run.summary)

    def test_unsubscribe_headers(self):
        self.subscriber()
        self.run_command()
        message = self.messages()[0]
        self.assertTrue(message["List-Unsubscribe"].startswith(f"<https://digest.example.org/digest/unsubscribe/"))
        self.assertEqual(message["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertIsNotNone(message.get_body(("plain",)))
        self.assertIsNotNone(message.get_body(("html",)))

    def test_nothing_to_send_is_skipped_and_counted(self):
        Event.objects.all().delete()
        subscriber = self.subscriber()
        self.run_command()
        self.assertEqual(self.ses.sent, [])
        self.assertIn(["skipped (no shows)", 1], JobRun.objects.get().summary)
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.last_digest_week)

    def test_run_twice_in_a_week_sends_once(self):
        self.subscriber()
        self.run_command()
        self.run_command()
        self.assertEqual(len(self.ses.sent), 1)

    def test_next_week_sends_again(self):
        self.subscriber()
        self.run_command()
        self.now += datetime.timedelta(days=7)
        Event.objects.create(title="Next week show", starttime=at(8), venue=self.venue)
        self.run_command()
        self.assertEqual(len(self.ses.sent), 2)

    def test_a_manual_sunday_rerun_is_still_the_same_week(self):
        self.subscriber()
        self.run_command()
        self.now = datetime.datetime(2026, 11, 8, 15, 0, tzinfo=datetime.timezone.utc)
        self.run_command()
        self.assertEqual(len(self.ses.sent), 1)
        # and a subscriber added since is sent that Monday's week, with a window from Sunday
        late = self.subscriber("late@example.com")
        Event.objects.create(title="Sunday show", starttime=at(3), venue=self.venue)
        Event.objects.create(title="Saturday show", starttime=at(2), venue=self.venue)
        self.run_command()
        late.refresh_from_db()
        self.assertEqual(late.last_digest_week, MONDAY)
        text = body(self.messages()[-1])
        self.assertIn("Sunday show", text)
        self.assertNotIn("Saturday show", text)

    def test_paused_and_unconfirmed_are_skipped(self):
        self.subscriber("paused@example.com", paused=True)
        self.subscriber("new@example.com", confirmed_at=None)
        self.run_command()
        self.assertEqual(self.ses.sent, [])

    def test_dry_run_sends_and_records_nothing(self):
        subscriber = self.subscriber()
        old = Subscriber.objects.create(email="old@example.com", created_at=self.now)
        Subscriber.objects.filter(pk=old.pk).update(created_at=self.now - datetime.timedelta(days=9))
        self.run_command("--dry-run")
        self.assertEqual(self.ses.sent, [])
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.last_digest_week)
        self.assertIn(f"would send subscriber {subscriber.pk}", self.output)
        self.assertTrue(Subscriber.objects.filter(pk=old.pk).exists())

    def test_limit(self):
        for i in range(3):
            self.subscriber(f"fan{i}@example.com")
        self.run_command("--limit", "2")
        self.assertEqual(self.addresses(), ["fan0@example.com", "fan1@example.com"])
        self.run_command()
        self.assertEqual(self.addresses()[2:], ["fan2@example.com"])

    def test_a_deleted_venue_sends_nothing_for_it(self):
        self.subscriber()
        self.venue.delete()
        self.run_command()
        self.assertEqual(self.ses.sent, [])


class FailureTestCase(SendTestCase):
    def test_one_failed_send_does_not_stop_the_rest_and_is_retried(self):
        first, second = self.subscriber("a@example.com"), self.subscriber("b@example.com")
        original = self.ses.send_raw_email
        calls = []

        def flaky(**kwargs):
            calls.append(kwargs["Destinations"][0])
            if kwargs["Destinations"] == ["a@example.com"]:
                raise ClientError({"Error": {"Code": "MessageRejected", "Message": "a@example.com rejected"}}, "SendRawEmail")
            return original(**kwargs)

        self.ses.send_raw_email = flaky
        with self.assertLogs("core.management.commands.send_weekly_digests", "ERROR") as logs, self.assertRaises(CommandError):
            self.run_command()
        self.assertEqual(self.addresses(), ["b@example.com"])
        self.assertEqual(JobRun.objects.get().status, JobRun.Status.FAILED)
        self.assertNotIn("a@example.com", "".join(logs.output) + self.output)
        self.assertIn(f"subscriber {first.pk}", "".join(logs.output))
        first.refresh_from_db()
        self.assertIsNone(first.last_digest_week)
        # the next run in the same week retries only the failed one
        self.ses.send_raw_email = original
        self.run_command()
        self.assertEqual(self.addresses(), ["b@example.com", "a@example.com"])

    def test_a_throttling_reply_is_a_failed_send(self):
        subscriber = self.subscriber()
        self.ses.error = ClientError({"Error": {"Code": "Throttling", "Message": "slow down"}}, "SendRawEmail")
        with self.assertRaises(CommandError):
            self.run_command()
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.last_digest_week)
        self.ses.error = None
        self.run_command()
        self.assertEqual(len(self.ses.sent), 1)

    def test_no_mail_service_credentials(self):
        self.subscriber()
        self.ses.error = NoCredentialsError()
        with self.assertRaises(CommandError):
            self.run_command()
        self.assertEqual(JobRun.objects.get().status, JobRun.Status.FAILED)
        self.assertIn(["failed", 1], JobRun.objects.get().summary)

    def test_placeholder_sender_sends_nothing(self):
        self.subscriber()
        with override_settings(DEFAULT_FROM_EMAIL="webmaster@localhost"), self.assertLogs(
            "core.management.commands.send_weekly_digests", "ERROR"
        ), self.assertRaises(CommandError):
            self.run_command()
        self.assertEqual(self.ses.sent, [])
        self.assertEqual(JobRun.objects.get().status, JobRun.Status.FAILED)

    def test_site_address_unset_blank_localhost_or_not_https(self):
        subscriber = self.subscriber()
        for site in ("", "http://localhost:8001", "http://digest.example.org"):
            with self.subTest(site=site), override_settings(SITE_URL=site), self.assertLogs(
                "core.management.commands.send_weekly_digests", "ERROR"
            ), self.assertRaises(CommandError):
                self.run_command()
        self.assertEqual(self.ses.sent, [])
        subscriber.refresh_from_db()
        self.assertIsNone(subscriber.last_digest_week)
        self.assertEqual(JobRun.objects.filter(status=JobRun.Status.FAILED).count(), 3)


class OverlapTestCase(SendTestCase):
    def test_two_overlapping_runs_send_each_subscriber_one_email(self):
        for i in range(3):
            self.subscriber(f"fan{i}@example.com")
        original = self.ses.send_raw_email
        nested = []

        def overlapping(**kwargs):
            # a second run starts while the first is sending its first email
            if not nested:
                nested.append(True)
                self.run_command()
            return original(**kwargs)

        self.ses.send_raw_email = overlapping
        self.run_command()
        self.assertEqual(sorted(self.addresses()), ["fan0@example.com", "fan1@example.com", "fan2@example.com"])


class CleanUpTestCase(SendTestCase):
    def test_old_unconfirmed_signups_codes_and_requests_are_deleted(self):
        old = Subscriber.objects.create(email="old@example.com")
        Subscriber.objects.filter(pk=old.pk).update(created_at=self.now - datetime.timedelta(days=8))
        recent = Subscriber.objects.create(email="recent@example.com")
        confirmed = self.subscriber()
        Subscriber.objects.filter(pk=confirmed.pk).update(created_at=self.now - datetime.timedelta(days=30))
        code = SignInCode.objects.create(subscriber=confirmed, code_hash="x")
        SignInCode.objects.filter(pk=code.pk).update(created_at=self.now - datetime.timedelta(days=2))
        request = MailRequest.objects.create(kind="mail", address="a@example.com", created_at=self.now - datetime.timedelta(days=2))
        self.run_command()
        self.assertFalse(Subscriber.objects.filter(pk=old.pk).exists())
        self.assertTrue(Subscriber.objects.filter(pk=recent.pk).exists())
        self.assertTrue(Subscriber.objects.filter(pk=confirmed.pk).exists())
        self.assertFalse(SignInCode.objects.exists())
        self.assertFalse(MailRequest.objects.filter(pk=request.pk).exists())
        self.assertIn(["deleted unconfirmed", 1], JobRun.objects.get().summary)
