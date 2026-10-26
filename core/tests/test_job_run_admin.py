import datetime

from core.models import JobRun, Venue
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

LIST_URL = "/admin/core/jobrun/"


class JobRunAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser("admin", "a@example.com", "pw")
        )
        now = timezone.now()
        self.killed = JobRun.objects.create(
            command="fetch_events", started_at=now - datetime.timedelta(hours=7)
        )
        self.running = JobRun.objects.create(
            command="fetch_events", started_at=now - datetime.timedelta(minutes=10)
        )
        self.failed = JobRun.objects.create(
            command="fetch_events",
            started_at=now - datetime.timedelta(minutes=1),
            finished_at=now,
            status=JobRun.Status.FAILED,
            error="CommandError: no event sources saved",
            output="fetching events for 0 venues...",
            summary=[["events created", 0]],
        )

    def test_killed_run_and_run_in_progress(self):
        response = self.client.get(LIST_URL)
        self.assertContains(response, "didn&#x27;t finish")
        self.assertContains(response, ">running<")
        stale = self.client.get(LIST_URL, {"outcome": "didn't finish"})
        self.assertEqual(list(stale.context["cl"].result_list), [self.killed])
        running = self.client.get(LIST_URL, {"outcome": "running"})
        self.assertEqual(list(running.context["cl"].result_list), [self.running])

    def test_failed_run_stands_out(self):
        response = self.client.get(LIST_URL)
        runs = list(response.context["cl"].result_list)
        self.assertEqual(runs[0], self.failed)
        self.assertContains(
            response, '<strong style="color: #cf222e">failed</strong>', html=True
        )
        self.assertContains(response, "events created 0")
        page = self.client.get(f"{LIST_URL}{self.failed.pk}/change/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "no event sources saved")
        self.assertContains(page, "fetching events for 0 venues...")

    def test_read_only(self):
        self.assertEqual(self.client.get(f"{LIST_URL}add/").status_code, 403)
        page = self.client.get(f"{LIST_URL}{self.failed.pk}/change/")
        for button in ("_save", "_saveasnew", "_addanother", "_continue"):
            self.assertNotContains(page, f'name="{button}"')
        self.client.post(f"{LIST_URL}{self.failed.pk}/change/", {"command": "changed"})
        self.failed.refresh_from_db()
        self.assertEqual(self.failed.command, "fetch_events")

    def test_title_uses_local_time(self):
        # started_at is stored in utc; the site's time zone is new york
        run = JobRun.objects.create(
            command="fetch_events",
            started_at=datetime.datetime(2026, 10, 26, 13, 39, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(str(run), "fetch_events 2026-10-26 09:39")

    def test_editable_pages_keep_every_save_button(self):
        venue = Venue.objects.create(name="Paradise Rock Club")
        page = self.client.get(f"/admin/core/venue/{venue.pk}/change/")
        for button in ("_save", "_saveasnew", "_addanother", "_continue"):
            self.assertContains(page, f'name="{button}"')

    def test_run_with_problems(self):
        rails = Venue.objects.create(sheet_id="V0316", name="Off The Rails")
        burren = Venue.objects.create(sheet_id="V0285", name="The Burren")
        run = JobRun.objects.create(
            command="fetch_events",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status=JobRun.Status.SUCCEEDED,
            problems=[
                {
                    "venue_id": rails.pk,
                    "sheet_id": "V0316",
                    "name": "Off The Rails",
                    "problems": ["failed: https://www.ticketweb.com/event/1 HttpError()"],
                },
                {
                    "venue_id": burren.pk,
                    "sheet_id": "V0285",
                    "name": "The Burren",
                    "problems": ["ai extraction failed: stopped with max_tokens"],
                },
            ],
            output="the report",
        )
        page = self.client.get(f"{LIST_URL}{run.pk}/change/").content.decode()
        self.assertIn("2 venues with problems", page)
        self.assertIn(f'href="/admin/core/venue/{rails.pk}/change/"', page)
        self.assertIn("stopped with max_tokens", page)
        # the failing page is a link, for spot checks
        self.assertIn(
            '<a target="_blank" rel="noopener" href="https://www.ticketweb.com/event/1">'
            "https://www.ticketweb.com/event/1</a> HttpError()",
            page,
        )
        # listed before the text report
        self.assertLess(page.index("2 venues with problems"), page.index("the report"))
        listing = self.client.get(LIST_URL)
        self.assertContains(listing, '<strong style="color: #cf222e">2</strong>', html=True)

    def test_run_without_problems(self):
        run = JobRun.objects.create(
            command="fetch_events",
            started_at=timezone.now(),
            finished_at=timezone.now(),
            status=JobRun.Status.SUCCEEDED,
        )
        page = self.client.get(f"{LIST_URL}{run.pk}/change/")
        self.assertContains(page, "no problems")
        listing = self.client.get(LIST_URL)
        self.assertContains(listing, '<td class="field-problem_count">0</td>', html=True)
