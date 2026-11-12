from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core import link_hubs
from core.management.commands import read_artist_link_hubs as command
from core.models import Artist, Band, JobRun
from core.tests.test_link_hubs import page

ROBOTS_OPEN = "User-agent: *\nAllow: /\n"
ROBOTS_CLOSED = "User-agent: *\nDisallow: /\n"
KRILL = "https://linktr.ee/krill"
SUNNY = "https://linktr.ee/sunnydaze"


def response(url, status=200, text="", location=None):
    headers = {"Location": location} if location else {}
    return SimpleNamespace(status_code=status, text=text, url=url, headers=headers)


class FakeSession:
    """answers get() from a dict of url -> response, text or exception; anything else is a 404"""

    def __init__(self, pages):
        self.pages = pages
        self.headers = {}
        self.requested = []

    def get(self, url, timeout=None, allow_redirects=True):
        self.requested.append(url)
        answer = self.pages.get(url)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            return response(url, 404)
        if isinstance(answer, str):
            return response(url, 200, answer)
        return answer


class ReadLinkHubsTestCase(TestCase):
    def run_command(self, pages, *args):
        pages = {"https://linktr.ee/robots.txt": ROBOTS_OPEN, **pages}
        self.session = FakeSession(pages)
        self.sleeps = []
        out = StringIO()
        with mock.patch.object(link_hubs.requests, "Session", return_value=self.session), mock.patch.object(
            link_hubs.time, "sleep", self.sleeps.append
        ):
            call_command("read_artist_link_hubs", *args, stdout=out)
        return out.getvalue()

    def pages_requested(self):
        return [url for url in self.session.requested if not url.endswith("/robots.txt")]

    def test_a_readable_hub(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: page("linktree.html")})
        band.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.link_hub_checked_at is not None), ("read", True))
        self.assertEqual(band.bandcamp_url, "https://krill.bandcamp.com/")
        self.assertEqual(band.instagram_url, "https://www.instagram.com/krill.band/")
        self.assertEqual(band.youtube_url, "https://www.youtube.com/channel/UC123")
        self.assertEqual(band.website, "")
        self.assertEqual({band.field_sources[n] for n in ("bandcamp_url", "instagram_url", "youtube_url")}, {"link hub"})
        self.assertEqual(self.pages_requested(), [KRILL])

    def test_nothing_but_the_hub_page_is_requested(self):
        Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: page("linktree.html")})
        self.assertEqual({link_hubs.host_of(url) for url in self.session.requested}, {"linktr.ee"})

    def test_robots_is_asked_once_per_hub(self):
        Band.objects.create(name="Krill", link_hub_url=KRILL)
        Artist.objects.create(name="Sunny Daze", link_hub_url=SUNNY)
        self.run_command({KRILL: page("linktree.html"), SUNNY: page("empty.html")})
        self.assertEqual(self.session.requested.count("https://linktr.ee/robots.txt"), 1)
        # and at most a request a second
        self.assertEqual(len(self.sleeps), 2)

    def test_the_honest_user_agent(self):
        Band.objects.create(name="Krill", link_hub_url=KRILL)
        with mock.patch.object(link_hubs.requests, "Session") as session:
            session.return_value = FakeSession({"https://linktr.ee/robots.txt": ROBOTS_OPEN, KRILL: page("empty.html")})
            call_command("read_artist_link_hubs", stdout=StringIO())
        self.assertIn("venue-db-event-check/1.0", session.return_value.headers["User-Agent"])

    def test_robots_forbids_it(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({"https://linktr.ee/robots.txt": ROBOTS_CLOSED, KRILL: page("linktree.html")})
        band.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.instagram_url), ("blocked", ""))
        self.assertEqual(self.pages_requested(), [])

    def test_a_blocked_page(self):
        for status in (403, 406, 429):
            band = Band.objects.create(name=f"Krill {status}", link_hub_url=f"{KRILL}{status}")
            self.run_command({f"{KRILL}{status}": response(f"{KRILL}{status}", status)})
            band.refresh_from_db()
            self.assertEqual(band.link_hub_status, "blocked", status)

    def test_a_deleted_hub_page(self):
        band = Band.objects.create(
            name="Krill", link_hub_url=KRILL, instagram_url="https://www.instagram.com/old/", field_sources={"instagram_url": "link hub"}
        )
        self.run_command({})
        band.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.instagram_url), ("gone", "https://www.instagram.com/old/"))

    def test_a_hub_that_cant_be_read(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        other = Band.objects.create(name="Sunny Daze", link_hub_url=SUNNY)
        self.run_command({KRILL: page("scripted.html"), SUNNY: page("anchors.html")})
        band.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.link_hub_url), ("unreadable", KRILL))
        self.assertEqual(other.link_hub_status, "read")

    def test_a_page_with_no_links(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: page("empty.html")})
        band.refresh_from_db()
        self.assertEqual(band.link_hub_status, "empty")

    def test_an_address_only_hub(self):
        band = Band.objects.create(name="Krill", link_hub_url="https://taplink.cc/krill")
        self.run_command({"https://taplink.cc/krill": page("anchors.html")})
        band.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.link_hub_url, band.instagram_url), ("unreadable", "https://taplink.cc/krill", ""))
        self.assertEqual(self.session.requested, [])

    def test_recently_read_records_are_skipped(self):
        recent = timezone.now() - timedelta(days=3)
        band = Band.objects.create(name="Krill", link_hub_url=KRILL, link_hub_status="read", link_hub_checked_at=recent)
        self.run_command({KRILL: page("linktree.html")})
        self.assertEqual(self.session.requested, [])
        band.refresh_from_db()
        self.assertEqual(band.instagram_url, "")
        # --refresh reads it anyway, and a week-old read is due without it
        self.run_command({KRILL: page("linktree.html")}, "--refresh")
        band.refresh_from_db()
        self.assertEqual(band.instagram_url, "https://www.instagram.com/krill.band/")
        Band.objects.filter(pk=band.pk).update(link_hub_checked_at=timezone.now() - timedelta(days=8))
        self.run_command({KRILL: page("empty.html")})
        self.assertEqual(self.pages_requested(), [KRILL])

    def test_a_redirect_off_the_hub(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: response(KRILL, 301, location="https://elsewhere.example/krill")})
        band.refresh_from_db()
        self.assertEqual(band.link_hub_status, "failed")
        self.assertNotIn("https://elsewhere.example/krill", self.session.requested)

    def test_a_redirect_on_the_hub_is_followed(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: response(KRILL, 301, location="/krill/"), "https://linktr.ee/krill/": page("linktree.html")})
        band.refresh_from_db()
        self.assertEqual(band.link_hub_status, "read")

    def test_one_failure_doesnt_stop_the_run(self):
        Band.objects.create(name="Aardvark", link_hub_url="https://linktr.ee/aardvark")
        Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({"https://linktr.ee/aardvark": requests.Timeout("slow"), KRILL: page("linktree.html")})
        self.assertEqual(Band.objects.get(name="Aardvark").link_hub_status, "failed")
        self.assertEqual(Band.objects.get(name="Krill").link_hub_status, "read")
        run = JobRun.objects.get(command="read_artist_link_hubs")
        self.assertEqual(dict(run.summary), {"read": 1, "filled": 3, "flagged": 0, "failed": 1})
        self.assertEqual(run.problems, [{"venue_id": None, "sheet_id": "", "name": "Aardvark (band)", "problems": ["failed"]}])

    def test_a_blocked_act_in_the_job_run(self):
        Artist.objects.create(name="Sunny Daze", link_hub_url=SUNNY)
        self.run_command({SUNNY: response(SUNNY, 429)})
        run = JobRun.objects.get(command="read_artist_link_hubs")
        self.assertEqual(run.problems, [{"venue_id": None, "sheet_id": "", "name": "Sunny Daze (artist)", "problems": ["blocked"]}])
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        html = self.client.get(reverse("admin:core_jobrun_change", args=[run.pk])).content.decode()
        self.assertIn("1 records with problems", html)
        self.assertIn("Sunny Daze (artist)", html)
        self.assertIn("blocked", html)

    def test_the_run_is_listed_with_its_summary(self):
        Band.objects.create(name="Krill", link_hub_url=KRILL)
        self.run_command({KRILL: page("linktree.html")})
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        html = self.client.get(reverse("admin:core_jobrun_changelist")).content.decode()
        self.assertIn("read_artist_link_hubs", html)
        self.assertIn("read 1 · filled 3", html)

    def test_the_limit_and_the_oldest_first(self):
        Band.objects.create(name="Krill", link_hub_url=KRILL, link_hub_checked_at=timezone.now() - timedelta(days=30))
        Artist.objects.create(name="Sunny Daze", link_hub_url=SUNNY)
        self.run_command({KRILL: page("empty.html"), SUNNY: page("empty.html")}, "--limit", "1")
        self.assertEqual(self.pages_requested(), [SUNNY])

    def test_a_dry_run_saves_nothing(self):
        band = Band.objects.create(name="Krill", link_hub_url=KRILL)
        artist = Artist.objects.create(name="Sunny Daze", website=SUNNY, field_sources={"website": "import"})
        out = self.run_command({KRILL: page("linktree.html"), SUNNY: page("anchors.html")}, "--dry-run")
        self.assertEqual(len(self.pages_requested()), 2)
        self.assertIn("instagram_url from the hub", out)
        band.refresh_from_db()
        artist.refresh_from_db()
        self.assertEqual((band.link_hub_status, band.instagram_url, artist.link_hub_url), ("", "", ""))


class HubAddressFromTheWebsiteTestCase(TestCase):
    run_command = ReadLinkHubsTestCase.run_command
    pages_requested = ReadLinkHubsTestCase.pages_requested

    def test_a_hub_address_as_the_website(self):
        artist = Artist.objects.create(name="Sunny Daze", website=SUNNY, field_sources={"website": "import"})
        self.run_command({SUNNY: page("anchors.html")})
        artist.refresh_from_db()
        self.assertEqual((artist.link_hub_url, artist.field_sources["link_hub_url"]), (SUNNY, "import"))
        self.assertEqual((artist.website, artist.field_sources["website"]), (SUNNY, "import"))
        self.assertEqual(artist.link_hub_status, "read")
        self.assertEqual(artist.instagram_url, "https://instagram.com/sunnydaze")
        # a real site on the hub is a finding on the website
        self.assertEqual([(f["field"], f["current"], f["hub"]) for f in artist.link_hub_findings], [("website", SUNNY, "https://sunnydaze.com")])

    def test_the_copy_follows_a_changed_website(self):
        artist = Artist.objects.create(name="Sunny Daze", website=SUNNY, field_sources={"website": "import"})
        self.run_command({SUNNY: page("empty.html")})
        Artist.objects.filter(pk=artist.pk).update(website="https://linktr.ee/sunny", link_hub_checked_at=None)
        self.run_command({"https://linktr.ee/sunny": page("empty.html")})
        self.assertEqual(Artist.objects.get(pk=artist.pk).link_hub_url, "https://linktr.ee/sunny")

    def test_an_editors_address_is_not_copied_over(self):
        for source in ("editor", "musicbrainz"):
            artist = Artist.objects.create(
                name=f"Sunny {source}", website=SUNNY, link_hub_url=KRILL, field_sources={"website": "import", "link_hub_url": source}
            )
            self.run_command({KRILL: page("empty.html")})
            self.assertEqual(Artist.objects.get(pk=artist.pk).link_hub_url, KRILL)

    def test_a_website_that_is_not_a_hub_is_ignored(self):
        Artist.objects.create(name="Sunny Daze", website="https://sunnydaze.com")
        self.run_command({})
        self.assertEqual(self.session.requested, [])
