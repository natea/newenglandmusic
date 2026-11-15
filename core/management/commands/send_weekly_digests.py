import datetime
import logging
import time

from botocore.exceptions import BotoCoreError, ClientError
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from core import digest, digest_mail, digest_tokens
from core.job_runs import RecordedCommand
from core.models import SignInCode, Subscriber

"""
sends each confirmed, unpaused subscriber the weekly email: the shows their choices select from
today through the seventh day after, once a week.

run as:

python manage.py send_weekly_digests [--dry-run] [--limit 100]
python manage.py send_weekly_digests --to fan@example.com    # one subscriber's email now, as a test

a subscriber is claimed for the week (Subscriber.last_digest_week, the monday on or before today,
New York time) before their email is sent, so overlapping runs can't both send, and released if
the send fails, so the next run in the same week tries again. nobody with no selected shows gets
an email. it also deletes sign-ups never confirmed after 7 days, and old sign-in codes and
mail request rows. logs name a subscriber by id, never by address.
"""

logger = logging.getLogger(__name__)

UNCONFIRMED_AFTER = datetime.timedelta(days=7)
# the account sends 14 a second at first; stay well under it
PAUSE = 0.15


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="build every email, send none and record nothing")
        parser.add_argument("--limit", type=int, help="look at at most this many subscribers")
        parser.add_argument(
            "--to", metavar="ADDRESS",
            help="send this one confirmed subscriber their email now, as a test: it doesn't count as the week's, "
            "and nobody else is sent anything or cleaned up",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        now = timezone.now()
        today = now.astimezone(digest.NEW_YORK).date()
        if options["to"]:
            return self.send_test(options["to"], today)
        week = digest.week_of(today)
        counts = {"sent": 0, "skipped (no shows)": 0, "skipped (already sent or claimed)": 0, "failed": 0, "deleted unconfirmed": 0}
        self.job_summary = list(counts.items())
        if not self.dry_run:
            counts["deleted unconfirmed"] = self.clean_up(now)
            try:
                digest_mail.check_ready()
            except digest_mail.MailNotReady as error:
                self.job_summary = list(counts.items())
                logger.error("weekly email not sent: %s", error)
                raise CommandError(f"nothing sent: {error}")

        subscribers = Subscriber.objects.filter(confirmed_at__isnull=False, paused=False).filter(
            Q(last_digest_week__isnull=True) | Q(last_digest_week__lt=week)
        ).order_by("pk")
        if options["limit"]:
            subscribers = subscribers[: options["limit"]]
        window = digest.send_window(today)
        venues = digest.located_venues()
        heading = "would send" if self.dry_run else "sending"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} the week of {week}"))
        for subscriber in list(subscribers):
            self.send_one(subscriber, window, venues, week, today, counts)
        self.job_summary = list(counts.items())
        for label, count in counts.items():
            self.stdout.write(f"{label}: {count}")
        if counts["failed"]:
            raise CommandError(f"{counts['failed']} send(s) failed; they are tried again on the next run this week")

    def send_one(self, subscriber, window, venues, week, today, counts):
        events = list(digest.events_for(subscriber, window, venues))
        if not events:
            counts["skipped (no shows)"] += 1
            return
        subject, text, html, headers = digest.build_weekly(subscriber, events, digest_mail.site_url)
        if self.dry_run:
            counts["sent"] += 1
            self.stdout.write(f"would send subscriber {subscriber.pk}: {len(events)} shows")
            return
        previous = subscriber.last_digest_week
        claimed = Subscriber.objects.filter(pk=subscriber.pk, confirmed_at__isnull=False, paused=False).filter(
            Q(last_digest_week__isnull=True) | Q(last_digest_week__lt=week)
        ).update(last_digest_week=week)
        if not claimed:
            counts["skipped (already sent or claimed)"] += 1
            return
        try:
            digest_mail.send(subscriber.email, subject, text, html, headers=headers)
        except (ClientError, BotoCoreError, ValueError, digest_mail.MailNotReady) as error:
            # the class name only: a message could hold the address
            Subscriber.objects.filter(pk=subscriber.pk, last_digest_week=week).update(last_digest_week=previous)
            counts["failed"] += 1
            logger.error("couldn't send the weekly email to subscriber %s: %s", subscriber.pk, type(error).__name__)
            self.stderr.write(f"failed: subscriber {subscriber.pk}: {type(error).__name__}")
        else:
            counts["sent"] += 1
            time.sleep(PAUSE)

    def send_test(self, address, today):
        """
        one confirmed, unpaused subscriber's email for this week, sent now. the week isn't
        claimed, so the scheduled run still sends theirs
        """
        self.job_summary = [("sent", 0)]
        subscriber = Subscriber.objects.filter(email__iexact=address.strip(), confirmed_at__isnull=False).first()
        # the address isn't echoed back: errors and logs name subscribers by id
        if subscriber is None:
            raise CommandError("no confirmed subscriber has that address")
        if subscriber.paused:
            raise CommandError(f"subscriber {subscriber.pk} has paused the weekly email; nothing sent")
        events = list(digest.events_for(subscriber, digest.send_window(today)))
        if not events:
            raise CommandError(f"subscriber {subscriber.pk}'s choices select no shows this week; nothing sent")
        subject, text, html, headers = digest.build_weekly(subscriber, events, digest_mail.site_url)
        if self.dry_run:
            self.stdout.write(f"would send subscriber {subscriber.pk} a test: {len(events)} shows")
            return
        try:
            digest_mail.check_ready()
            digest_mail.send(subscriber.email, subject, text, html, headers=headers)
        except digest_mail.MailNotReady as error:
            raise CommandError(f"nothing sent: {error}")
        except (ClientError, BotoCoreError, ValueError) as error:
            raise CommandError(f"the test to subscriber {subscriber.pk} failed: {type(error).__name__}")
        self.job_summary = [("sent", 1)]
        self.stdout.write(self.style.SUCCESS(f"sent subscriber {subscriber.pk} a test: {len(events)} shows"))

    def clean_up(self, now):
        """deletes sign-ups never confirmed after a week, and old codes and mail request rows"""
        gone = Subscriber.objects.filter(confirmed_at__isnull=True, created_at__lt=now - UNCONFIRMED_AFTER).delete()[0]
        SignInCode.objects.filter(created_at__lt=now - datetime.timedelta(days=1)).delete()
        digest_tokens.delete_old_requests()
        return gone
