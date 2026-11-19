"""preview-environments: what a preview may hold of the live site's data"""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core import preview_data
from core.management.commands.set_preview_admin import set_admin
from core.models import DigestChoice, EmailSubscriber, Event, JobRun, MailRequest, SignInCode, Subscriber


class ClassifiedTestCase(TestCase):
    """Every table is classified"""

    def test_every_table_is_on_one_list(self):
        tables = connection.introspection.table_names()
        self.assertEqual(preview_data.unclassified(tables), [])
        lists = list(preview_data.LEFT_OUT) + list(preview_data.CLEANED) + list(preview_data.COPIED)
        self.assertEqual(len(lists), len(set(lists)), "a table is on two lists")
        self.assertEqual(sorted(set(lists) - set(tables)), [], "a listed table doesn't exist")

    def test_a_new_table(self):
        self.assertEqual(preview_data.unclassified(["core_event", "core_donor"]), ["core_donor"])

    def test_no_kept_table_points_at_a_left_out_one(self):
        with connection.cursor() as cursor:
            for table in list(preview_data.COPIED) + list(preview_data.CLEANED):
                for column, (_, other) in connection.introspection.get_relations(cursor, table).items():
                    self.assertNotIn(other, preview_data.LEFT_OUT, f"{table}.{column} points at {other}")

    def test_the_dump_leaves_their_rows_out(self):
        self.assertIn("--exclude-table-data=public.django_admin_log", preview_data.dump_exclusions())
        self.assertEqual(len(preview_data.dump_exclusions()), len(preview_data.LEFT_OUT))


class ScrubTestCase(TestCase):
    """People's data never reaches the copy"""

    def setUp(self):
        subscriber = Subscriber.objects.create(email="sooz@example.com")
        self.models = [Subscriber, EmailSubscriber, SignInCode, DigestChoice, MailRequest]
        EmailSubscriber.objects.create(email="mark@example.com")
        get_user_model().objects.create_superuser("nate", "nate@example.com", "a live password")
        self.client.login(username="nate", password="a live password")
        Event.objects.create(
            title="An unapproved show", starttime=timezone.now(), user_submitted=True, is_approved=False,
            user_submission_email="fan@example.com",
        )
        JobRun.objects.create(command="fetch_events", started_at=timezone.now(), output="Traceback …", error="boom")
        self.subscriber = subscriber

    def test_people_only_tables(self):
        preview_data.scrub(connection)
        self.assertEqual(Subscriber.objects.count(), 0)
        self.assertEqual(EmailSubscriber.objects.count(), 0)
        with connection.cursor() as cursor:
            for table in preview_data.LEFT_OUT:
                cursor.execute(f"SELECT count(*) FROM {connection.ops.quote_name(table)}")
                self.assertEqual(cursor.fetchone()[0], 0, table)

    def test_personal_fields(self):
        preview_data.scrub(connection)
        self.assertEqual(get_user_model().objects.count(), 0)
        event = Event.all_objects.get(title="An unapproved show")
        self.assertIsNone(event.user_submission_email)
        self.assertFalse(event.is_approved)
        run = JobRun.objects.get()
        self.assertEqual((run.output, run.error, run.command), ("", "", "fetch_events"))


class RefusalTestCase(SimpleTestCase):
    def test_other_settings(self):
        self.assertIn("nycnoise.settings.preview", preview_data.refusal("nycnoise.settings.prod", "localhost"))

    def test_another_database(self):
        self.assertIn("render.com", preview_data.refusal(preview_data.PREVIEW_SETTINGS, "dpg-abc.virginia-postgres.render.com"))

    def test_where_it_may_run(self):
        for host in ("localhost", "", "ep-cool-1.us-east-1.aws.neon.tech"):
            self.assertIsNone(preview_data.refusal(preview_data.PREVIEW_SETTINGS, host))

    def test_the_commands_refuse_here(self):
        for command in ("scrub_preview_data", "set_preview_admin"):
            with self.assertRaises(CommandError):
                call_command(command)


class PreviewAdminTestCase(TestCase):
    """A preview has its own admin"""

    def test_signing_in_as_the_preview_admin(self):
        set_admin(make_password("a long preview password"))
        user = authenticate(username="preview-admin", password="a long preview password")
        self.assertTrue(user and user.is_staff and user.is_superuser)
        set_admin(make_password("a newer preview password"))
        self.assertIsNone(authenticate(username="preview-admin", password="a long preview password"))
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_a_live_account(self):
        get_user_model().objects.create_superuser("nate", "nate@example.com", "a live password")
        set_admin(make_password("a long preview password"))
        self.assertIsNone(authenticate(username="nate", password="a live password"))
        self.assertEqual(list(get_user_model().objects.values_list("username", flat=True)), ["preview-admin"])

    def test_no_hash(self):
        with self.assertRaises(CommandError):
            set_admin("")
        with self.assertRaises(CommandError):
            set_admin("just-a-password")


class PreviewSettingsTestCase(SimpleTestCase):
    """A preview never reaches the outside world"""

    def test_the_preview_settings(self):
        from nycnoise.settings import preview

        self.assertTrue(preview.PREVIEW)
        self.assertEqual(preview.ALLOWED_HOSTS, [".run.app"])
        self.assertEqual(preview.CANONICAL_HOST, "")
        self.assertEqual(preview.DEFAULT_FROM_EMAIL, "")
        self.assertEqual(preview.DATABASES["default"]["CONN_MAX_AGE"], 0)
        self.assertFalse(preview.DEBUG)
        # above whitenoise, so static files carry the header too
        middleware = preview.MIDDLEWARE
        self.assertLess(middleware.index("core.middleware.NoIndexMiddleware"), middleware.index("whitenoise.middleware.WhiteNoiseMiddleware"))

    def test_not_indexed(self):
        from django.http import HttpResponse

        from core.middleware import NoIndexMiddleware

        for response in (HttpResponse("a page"), HttpResponse(b"a static file", content_type="text/css")):
            self.assertEqual(NoIndexMiddleware(lambda request: response)(None)["X-Robots-Tag"], "noindex, nofollow")

    def test_signing_up_for_the_weekly_email(self):
        from core import digest_mail

        with self.settings(DEFAULT_FROM_EMAIL="", SITE_URL="https://preview-pr-73-abc.a.run.app"):
            with self.assertRaises(digest_mail.MailNotReady):
                digest_mail.check_ready()


class DataExportTestCase(TestCase):
    def test_the_data_export(self):
        headers = {"Authorization": "Bearer " + "0xdeadbeef"}
        with self.settings(PREVIEW=True):
            self.assertEqual(self.client.get("/internal-api/db", headers=headers).status_code, 404)
            self.assertEqual(self.client.get("/internal-api/db").status_code, 404)
        self.assertEqual(self.client.get("/internal-api/db", headers=headers).status_code, 200)
