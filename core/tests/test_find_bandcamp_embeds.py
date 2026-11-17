from datetime import timedelta
from io import StringIO
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core import bandcamp_embeds
from core.management.commands import find_bandcamp_embeds as command
from core.models import Artist, Band, Event, EventPerformer, JobRun
from core.tests.test_bandcamp_embeds import FakeSession, page, player, reply

ROBOTS_CLOSED = "User-agent: *\nDisallow: /\n"
KRILL = "https://krill.bandcamp.com/"
SUNNY = "https://sunnydaze.bandcamp.com/"
ALBUM = {"album": page("album_redirect.html"), player("album", "111"): page("player_available.html")}


def days_ago(days):
    return timezone.now() - timedelta(days=days)


def found_band(name="Krill", url=KRILL, days=400, **fields):
    return Band.objects.create(
        name=name, bandcamp_url=url, bandcamp_embed_kind="album", bandcamp_embed_id="5", bandcamp_embed_status="found",
        bandcamp_embed_for=url, bandcamp_embed_checked_at=days_ago(days), **fields,
    )


def album_page(url):
    return {url: page("album_redirect.html")}


class FindBandcampEmbedsTestCase(TestCase):
    def run_command(self, pages=None, *args):
        pages = {**album_page(KRILL), player("album", "111"): page("player_available.html"), **(pages or {})}
        self.session = FakeSession(pages)
        self.sleeps = []
        out = StringIO()
        with mock.patch.object(bandcamp_embeds.requests, "Session", return_value=self.session), mock.patch.object(
            bandcamp_embeds.time, "sleep", self.sleeps.append
        ), mock.patch.object(command, "rebake_events_of", wraps=command.rebake_events_of) as rebake:
            call_command("find_bandcamp_embeds", *args, stdout=out)
        self.rebaked = [act.name for call in rebake.call_args_list for act in call.args[0]]
        return out.getvalue()

    def requests_made(self):
        return self.session.pages_requested()

    def test_a_player_is_found_and_only_its_kind_and_id_are_kept(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command()
        band.refresh_from_db()
        self.assertEqual(
            (band.bandcamp_embed_kind, band.bandcamp_embed_id, band.bandcamp_embed_status, band.bandcamp_embed_for),
            ("album", "111", "found", KRILL),
        )
        self.assertIsNotNone(band.bandcamp_embed_checked_at)
        self.assertTrue(band.bandcamp_player_usable)
        self.assertEqual(self.requests_made(), [KRILL, player("album", "111")])
        # nothing from the page: the other fields are as they were
        self.assertEqual((band.notes, band.website, band.field_sources), ("", "", {}))
        self.assertEqual(self.rebaked, ["Krill"])

    def test_requests_are_two_seconds_apart(self):
        Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command()
        self.assertTrue(self.sleeps and all(1 < wait <= 2 for wait in self.sleeps))

    def test_robots_forbids_it(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command({KRILL + "robots.txt": ROBOTS_CLOSED})
        band.refresh_from_db()
        self.assertEqual(band.bandcamp_embed_status, "blocked")
        self.assertEqual(self.requests_made(), [])

    def test_a_deleted_page(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command({KRILL: reply(KRILL, 404)})
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_status, band.bandcamp_url), ("gone", KRILL))

    def test_a_redirect_off_bandcamp(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command({KRILL: reply(KRILL, 301, location="https://example.com/krill")})
        band.refresh_from_db()
        self.assertEqual(band.bandcamp_embed_status, "failed")
        self.assertEqual(self.requests_made(), [KRILL])

    def test_no_playable_release(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command({player("album", "111"): page("player_unavailable.html")})
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_status, band.bandcamp_embed_id, band.bandcamp_embed_kind), ("no_playable", "", ""))
        self.assertEqual(len(self.requests_made()), 2)

    def test_a_failed_refresh_of_a_found_player(self):
        gone = found_band("Krill")
        busy = found_band("Sunny Daze", SUNNY)
        before = gone.bandcamp_embed_checked_at
        self.run_command({KRILL: reply(KRILL, 404), SUNNY: reply(SUNNY, 429)})
        for band in (gone, busy):
            band.refresh_from_db()
            self.assertEqual((band.bandcamp_embed_id, band.bandcamp_embed_status, band.bandcamp_embed_for), ("5", "found", band.bandcamp_url))
            self.assertTrue(band.bandcamp_embed_checked_at > before)
            self.assertTrue(band.bandcamp_player_usable)
        run = JobRun.objects.get(command="find_bandcamp_embeds")
        self.assertEqual(
            sorted((p["name"], p["problems"]) for p in run.problems),
            [("Krill (band)", ["gone"]), ("Sunny Daze (band)", ["blocked"])],
        )
        self.assertEqual(self.rebaked, [])

    def test_a_failed_refresh_keeps_the_id(self):
        band = found_band()
        self.run_command({KRILL: reply(KRILL, 500)})
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_id, band.bandcamp_embed_status), ("5", "found"))
        # tried again at the next due time: a year on
        self.assertTrue(command.bandcamp_embeds.due(band, timezone.now() + timedelta(days=366)))
        self.assertFalse(command.bandcamp_embeds.due(band, timezone.now() + timedelta(days=30)))

    def test_blocked_repeatedly(self):
        names = ["A", "B", "C", "D", "E"]
        for i, name in enumerate(names):
            Band.objects.create(name=name, bandcamp_url=f"https://{name.lower()}.bandcamp.com/")
        pages = {f"https://{n.lower()}.bandcamp.com/": reply("", 429) for n in names}
        out = self.run_command(pages)
        self.assertEqual(len(self.requests_made()), 3)
        self.assertEqual(Band.objects.filter(bandcamp_embed_status="blocked").count(), 3)
        self.assertIn("stopped", out)
        self.assertEqual(Band.objects.filter(bandcamp_embed_status="").count(), 2)
        run = JobRun.objects.get(command="find_bandcamp_embeds")
        self.assertTrue(any("stopped" in p["name"] for p in run.problems))

    def test_challenged_from_a_server_stops_the_run(self):
        # bandcamp sends servers its bot challenge with a 200: three in a row stop the run, and
        # nothing is marked unreadable
        names = ["A", "B", "C", "D", "E"]
        for name in names:
            Band.objects.create(name=name, bandcamp_url=f"https://{name.lower()}.bandcamp.com/")
        out = self.run_command({f"https://{n.lower()}.bandcamp.com/": page("challenge.html") for n in names})
        self.assertIn("stopped", out)
        self.assertEqual(Band.objects.filter(bandcamp_embed_status="blocked").count(), 3)
        self.assertFalse(Band.objects.filter(bandcamp_embed_status="unreadable").exists())

    def test_a_block_does_not_count_when_something_between_succeeded(self):
        for name in "ABCD":
            Band.objects.create(name=name, bandcamp_url=f"https://{name.lower()}.bandcamp.com/")
        pages = {
            "https://a.bandcamp.com/": reply("", 429), "https://b.bandcamp.com/": reply("", 429),
            "https://c.bandcamp.com/": page("album_redirect.html"), "https://d.bandcamp.com/": reply("", 429),
        }
        self.run_command(pages)
        self.assertEqual(Band.objects.filter(bandcamp_embed_status="").count(), 0)

    def test_never_looked_up(self):
        Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command()
        self.assertEqual(len(self.requests_made()), 2)

    def test_an_act_without_an_address(self):
        Band.objects.create(name="Krill")
        self.run_command()
        self.assertEqual(self.requests_made(), [])

    def test_recently_looked_up(self):
        found_band(days=30)
        self.run_command()
        self.assertEqual(self.requests_made(), [])

    def test_old_no_playable_result(self):
        Band.objects.create(name="Krill", bandcamp_url=KRILL, bandcamp_embed_status="no_playable", bandcamp_embed_for=KRILL, bandcamp_embed_checked_at=days_ago(100))
        self.run_command()
        self.assertEqual(Band.objects.get().bandcamp_embed_status, "found")

    def test_a_failed_lookup_is_not_repeated_weekly(self):
        for status in ("no_playable", "failed", "blocked"):
            Band.objects.create(
                name=status, bandcamp_url=f"https://{status.replace('_', '')}.bandcamp.com/", bandcamp_embed_status=status,
                bandcamp_embed_for=f"https://{status.replace('_', '')}.bandcamp.com/", bandcamp_embed_checked_at=days_ago(10),
            )
        out = self.run_command()
        self.assertEqual(self.requests_made(), [])
        self.assertIn("0 acts due", out)

    def test_an_editors_player_is_not_looked_up(self):
        Band.objects.create(
            name="Krill", bandcamp_url=KRILL, bandcamp_embed_kind="album", bandcamp_embed_id="7",
            field_sources={"bandcamp_embed": "editor"},
        )
        self.run_command(None, "--refresh")
        self.assertEqual(self.requests_made(), [])
        band = Band.objects.get()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id, band.bandcamp_embed_status), ("album", "7", ""))

    def test_a_declined_act_is_not_looked_up(self):
        Band.objects.create(name="Krill", bandcamp_url=KRILL, bandcamp_embed_status="declined")
        self.run_command(None, "--refresh")
        self.assertEqual(self.requests_made(), [])
        self.assertEqual(Band.objects.get().bandcamp_embed_status, "declined")

    def test_address_changed(self):
        band = found_band(days=30)
        Band.objects.filter(pk=band.pk).update(bandcamp_url=SUNNY)
        self.run_command(album_page(SUNNY))
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_id, band.bandcamp_embed_for), ("111", SUNNY))
        self.assertEqual(self.rebaked, ["Krill"])

    def test_address_changed_then_the_page_fails(self):
        for code in (404, 429, 500):
            with self.subTest(code=code):
                Band.objects.all().delete()
                band = found_band(days=30)
                Band.objects.filter(pk=band.pk).update(bandcamp_url=SUNNY)
                self.run_command({SUNNY: reply(SUNNY, code)})
                band.refresh_from_db()
                self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id), ("", ""))
                self.assertEqual(band.bandcamp_embed_for, SUNNY)
                self.assertNotEqual(band.bandcamp_embed_status, "found")
                self.assertFalse(band.bandcamp_player_usable)
                self.run_command({SUNNY: reply(SUNNY, code)})
                self.assertEqual(self.requests_made(), [])

    def test_dry_run(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        out = self.run_command(None, "--dry-run")
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_status, band.bandcamp_embed_checked_at, band.bandcamp_embed_for), ("", None, ""))
        self.assertIn("Krill (band): found (album 111)", out)
        self.assertEqual(self.rebaked, [])

    def test_limit(self):
        for n in range(10):
            Band.objects.create(name=f"Band {n:02}", bandcamp_url=f"https://b{n}.bandcamp.com/")
        self.run_command({f"https://b{n}.bandcamp.com/": page("empty.html") for n in range(10)}, "--limit", "3")
        self.assertEqual(Band.objects.exclude(bandcamp_embed_status="").count(), 3)

    def test_default_cap(self):
        Band.objects.bulk_create([Band(name=f"Band {n:03}", slug=f"b-{n}", bandcamp_url=f"https://b{n}.bandcamp.com/") for n in range(150)])
        self.run_command({f"https://b{n}.bandcamp.com/": reply("", 404) for n in range(150)})
        self.assertEqual(Band.objects.exclude(bandcamp_embed_status="").count(), 100)
        self.assertEqual(command.DEFAULT_LIMIT, 100)

    def test_refresh(self):
        found_band(days=10)
        self.run_command(None, "--refresh")
        self.assertEqual(Band.objects.get().bandcamp_embed_id, "111")

    def test_artists_too(self):
        Artist.objects.create(name="Solo", bandcamp_url=SUNNY)
        self.run_command(album_page(SUNNY))
        self.assertEqual(Artist.objects.get().bandcamp_embed_kind, "album")

    def test_an_editors_player_stays(self):
        # an editor saves a player after the run chose the band, before its turn comes
        stale = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        Band.objects.filter(pk=stale.pk).update(
            bandcamp_embed_kind="track", bandcamp_embed_id="9", field_sources={"bandcamp_embed": "editor"}
        )
        with mock.patch.object(command.Command, "records_due", return_value=[stale]):
            self.run_command()
        band = Band.objects.get()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id, band.bandcamp_embed_status), ("track", "9", ""))
        self.assertEqual(self.requests_made(), [])

    def test_a_page_view_asks_bandcamp_for_nothing(self):
        found_band()
        Band.objects.filter(name="Krill").update(needs_review=False)
        with mock.patch("requests.Session.request", side_effect=AssertionError("no requests")) as request:
            self.assertEqual(self.client.get("/").status_code, 200)
            self.assertEqual(self.client.get(Band.objects.get().get_absolute_url()).status_code, 200)
        request.assert_not_called()

    def test_the_run_is_recorded(self):
        Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.run_command()
        run = JobRun.objects.get(command="find_bandcamp_embeds")
        self.assertEqual(dict(map(tuple, run.summary)), {"looked up": 1, "found": 1, "no playable release": 0, "failed": 0})
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.assertEqual(self.client.get(reverse("admin:core_jobrun_changelist")).status_code, 200)

    def test_one_acts_trouble_does_not_stop_the_run(self):
        Band.objects.create(name="A", bandcamp_url="https://a.bandcamp.com/")
        Band.objects.create(name="B", bandcamp_url=KRILL)
        self.run_command({"https://a.bandcamp.com/": requests.Timeout()})
        self.assertEqual(Band.objects.get(name="A").bandcamp_embed_status, "failed")
        self.assertEqual(Band.objects.get(name="B").bandcamp_embed_status, "found")


class RebakeEventsOfTestCase(TestCase):
    def test_upcoming_events_of_the_acts_are_re_rendered(self):
        from core.event_performers import rebake_events_of

        band, other = Band.objects.create(name="Krill"), Band.objects.create(name="Pile")
        soon = Event.all_objects.create(title="soon", starttime=timezone.now() + timedelta(days=2))
        past = Event.all_objects.create(title="past", starttime=timezone.now() - timedelta(days=2))
        EventPerformer.objects.create(event=soon, band=band)
        EventPerformer.objects.create(event=past, band=band)
        self.assertEqual(rebake_events_of([band]), 1)
        self.assertEqual(rebake_events_of([other]), 0)
        self.assertEqual(rebake_events_of([]), 0)
