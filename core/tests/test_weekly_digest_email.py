import datetime
import re

from django.utils import timezone

from core import digest, digest_mail, digest_tokens
from core.models import DigestChoice, Event, Subscriber, Venue

from .digest_fixture import SITE, DigestTestCase

SEND_DAY = datetime.date(2026, 11, 5)


def at(days, hour=20):
    return datetime.datetime.combine(SEND_DAY + datetime.timedelta(days=days), datetime.time(hour), tzinfo=digest.NEW_YORK)


class WeeklyEmailTestCase(DigestTestCase):
    def setUp(self):
        super().setUp()
        self.venue = Venue.objects.create(name="The Sinclair", state="MA", city_town="Cambridge")
        self.subscriber = Subscriber.objects.create(email="fan@example.com", confirmed_at=timezone.now())
        DigestChoice.objects.create(subscriber=self.subscriber, kind="venue", venue=self.venue)

    def event(self, days, title="A show", hour=20, **extra):
        return Event.objects.create(title=title, starttime=at(days, hour), venue=self.venue, **extra)

    def build(self):
        events = digest.events_for(self.subscriber, digest.send_window(SEND_DAY))
        return digest.build_weekly(self.subscriber, events, digest_mail.site_url)

    def test_a_weeks_shows_grouped_by_date(self):
        self.event(0, "Day zero", artists="Mitski, Pond Bats")
        self.event(3, "Day three")
        self.event(8, "Day eight")
        _, text, html, _ = self.build()
        for part in (text, html):
            self.assertIn("Day zero", part)
            self.assertIn("Day three", part)
            self.assertNotIn("Day eight", part)
        self.assertIn("Thu Nov 5", text)
        self.assertIn("Sun Nov 8", text)
        self.assertLess(text.index("Day zero"), text.index("Day three"))
        self.assertIn("Mitski, Pond Bats", text)
        self.assertIn("The Sinclair, Cambridge", text)
        self.assertIn("8pm", text)

    def test_half_hour_times(self):
        Event.objects.create(title="Late", starttime=at(0, 21) + datetime.timedelta(minutes=30), venue=self.venue)
        self.assertIn("9:30pm", self.build()[1])

    def test_events_link_to_the_sites_own_page(self):
        event = self.event(1, hyperlink="https://tickets.example.net/x")
        _, text, html, _ = self.build()
        self.assertIn(f"{SITE}/event/{event.pk}", text)
        self.assertIn(f'href="{SITE}/event/{event.pk}"', html)
        self.assertNotIn("tickets.example.net", text + html)

    def test_cancelled_show_is_left_out(self):
        self.event(1, "Cancelled one", is_cancelled=True)
        self.event(1, "Going ahead")
        _, text, _, _ = self.build()
        self.assertNotIn("Cancelled one", text)
        self.assertIn("Going ahead", text)

    def test_both_parts_each_with_the_unsubscribe_and_sign_in_links(self):
        self.event(1)
        _, text, html, headers = self.build()
        link = headers["List-Unsubscribe"].strip("<>")
        self.assertTrue(link.startswith(f"{SITE}/digest/unsubscribe/"))
        for part in (text, html):
            self.assertIn(link, part)
            self.assertIn(f"{SITE}/digest/sign-in", part)

    def test_sixty_shows_list_fifty_and_a_see_all_link(self):
        for i in range(60):
            Event.objects.create(title=f"Show {i:02d}", starttime=at(1) + datetime.timedelta(minutes=i), venue=self.venue)
        _, text, html, _ = self.build()
        self.assertEqual(len(re.findall(r"^- Show", text, re.M)), 50)
        self.assertIn("Show 49", text)
        self.assertNotIn("Show 50", text)
        self.assertIn("See all 60 on the site: " + SITE + "/\n", text)
        self.assertIn(">See all 60 on the site<", html)

    def test_see_all_link_filters_to_the_first_area_choice(self):
        DigestChoice.objects.create(subscriber=self.subscriber, kind="area", area_query="state=massachusetts")
        for i in range(51):
            Event.objects.create(title=f"Show {i}", starttime=at(1) + datetime.timedelta(minutes=i), venue=self.venue)
        _, text, _, _ = self.build()
        self.assertIn(f"{SITE}/?state=massachusetts", text)

    def test_no_see_all_link_at_the_limit(self):
        for i in range(50):
            Event.objects.create(title=f"Show {i}", starttime=at(1) + datetime.timedelta(minutes=i), venue=self.venue)
        _, text, _, _ = self.build()
        self.assertNotIn("See all", text)

    def test_markup_in_a_title_is_escaped_and_the_subject_is_fixed(self):
        self.event(1, "<script>alert(1)</script>", artists="<b>Band</b> & co")
        subject, text, html, _ = self.build()
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;Band&lt;/b&gt; &amp; co", html)
        self.assertEqual(subject, digest.SUBJECT)
        self.assertNotIn("script", subject)
        self.assertIn("<script>alert(1)</script>", text)

    def test_a_line_break_in_a_title_stays_on_one_line_in_the_text(self):
        self.event(1, "Two\nlines")
        self.assertIn("Two lines", self.build()[1])

    def test_a_deleted_venue_drops_out(self):
        self.event(1, "Gone")
        self.venue.delete()
        self.assertEqual(self.build()[1].count("- "), 0)


class MailRoutesTestCase(DigestTestCase):
    def test_confirmation_and_code_emails_are_raw_multipart_without_unsubscribe_headers(self):
        subscriber = Subscriber.objects.create(email="fan@example.com", confirmed_at=timezone.now())
        digest_mail.send_confirmation(subscriber)
        digest_mail.send_code(subscriber, "123456")
        digest_mail.send_known(subscriber)
        self.assertEqual(len(self.ses.sent), 3)
        for message in self.messages():
            self.assertEqual(message.get_content_type(), "multipart/alternative")
            self.assertIsNotNone(message.get_body(("plain",)))
            self.assertIsNotNone(message.get_body(("html",)))
            self.assertNotIn("List-Unsubscribe", message)
            self.assertNotIn("List-Unsubscribe-Post", message)

    def test_an_address_with_a_line_break_builds_no_message(self):
        subscriber = Subscriber(email="a@example.com\nBcc: b@example.com")
        subscriber.pk = 1
        with self.assertRaises(ValueError):
            digest_mail.send_code(subscriber, "123456")
        self.assertEqual(self.ses.sent, [])

    def test_the_placeholder_sender_sends_nothing(self):
        from django.test import override_settings

        with override_settings(DEFAULT_FROM_EMAIL="webmaster@localhost"), self.assertRaises(digest_mail.MailNotReady):
            digest_mail.send("a@example.com", "s", "t", "<p>h</p>")
        self.assertEqual(self.ses.sent, [])

    def test_the_site_address_must_be_https_and_not_localhost(self):
        from django.test import override_settings

        for site in ("", "http://localhost:8001", "https://localhost", "http://example.org", "example.org"):
            with self.subTest(site=site), override_settings(SITE_URL=site), self.assertRaises(digest_mail.MailNotReady):
                digest_mail.check_ready()
        self.assertEqual(self.ses.sent, [])

    def test_unsubscribe_token_in_the_header_names_the_subscriber(self):
        subscriber = Subscriber.objects.create(email="fan@example.com", confirmed_at=timezone.now())
        token = digest_tokens.unsubscribe_token(subscriber)
        self.assertEqual(digest_tokens.subscriber_from(token, digest_tokens.UNSUBSCRIBE_SALT), subscriber)
