import os
import tempfile
from io import StringIO

from core.models import Artist, Band, JobRun
from django.core.management import call_command
from django.test import TestCase


class MarkInactiveActsTestCase(TestCase):
    def setUp(self):
        self.cars = Band.objects.create(name="The Cars")
        self.greg = Artist.objects.create(name="Greg Humphreys")

    def run_command(self, *args):
        out = StringIO()
        call_command("mark_inactive_acts", *args, stdout=out)
        return out.getvalue()

    def inactive(self):
        return {act.name for model in (Band, Artist) for act in model.objects.filter(is_inactive=True)}

    def file(self, text):
        handle, path = tempfile.mkstemp(suffix=".txt")
        self.addCleanup(os.remove, path)
        with os.fdopen(handle, "w") as file:
            file.write(text)
        return path

    def test_marking_by_slug(self):
        output = self.run_command("the-cars", "greg-humphreys")
        self.assertEqual(self.inactive(), {"The Cars", "Greg Humphreys"})
        self.assertIn("The Cars", output)
        self.assertIn("Greg Humphreys", output)

    def test_a_dry_run(self):
        output = self.run_command("--dry-run", "the-cars")
        self.assertIn("would mark inactive: The Cars", output)
        self.assertEqual(self.inactive(), set())

    def test_an_unknown_address(self):
        output = self.run_command("the-cars", "no-such-band")
        self.assertEqual(self.inactive(), {"The Cars"})
        self.assertIn("not found: no-such-band", output)

    def test_an_ambiguous_address(self):
        Band.objects.create(name="Orbit")
        Artist.objects.create(name="Orbit")
        output = self.run_command("orbit")
        self.assertEqual(self.inactive(), set())
        self.assertIn("ambiguous", output)
        self.assertIn("orbit", output)

    def test_a_kind_qualified_address(self):
        Band.objects.create(name="Orbit")
        Artist.objects.create(name="Orbit")
        self.run_command("bands/orbit")
        self.assertEqual((Band.objects.get(slug="orbit").is_inactive, Artist.objects.get(slug="orbit").is_inactive), (True, False))

    def test_a_qualified_address_of_the_wrong_kind_is_not_found(self):
        output = self.run_command("artists/the-cars")
        self.assertEqual(self.inactive(), set())
        self.assertIn("not found: artists/the-cars", output)

    def test_addresses_from_a_file(self):
        self.run_command("--file", self.file("the-cars\ngreg-humphreys\n"))
        self.assertEqual(self.inactive(), {"The Cars", "Greg Humphreys"})

    def test_comments_and_blank_lines_in_the_file(self):
        output = self.run_command("--file", self.file("# first batch\n\n  \nbands/the-cars\n"))
        self.assertEqual(self.inactive(), {"The Cars"})
        self.assertNotIn("not found", output)

    def test_a_job_run(self):
        self.run_command("the-cars", "greg-humphreys", "no-such-band")
        run = JobRun.objects.latest("pk")
        self.assertEqual((run.command, run.status), ("mark_inactive_acts", JobRun.Status.SUCCEEDED))
        self.assertEqual(run.summary, [["changed", 2]])

    def test_a_held_act(self):
        held = Band.objects.create(name="Held", needs_review=True)
        self.run_command("held")
        held.refresh_from_db()
        self.assertEqual((held.is_inactive, held.needs_review), (True, True))

    def test_reversing(self):
        self.run_command("the-cars")
        self.run_command("--active", "the-cars")
        self.assertEqual(self.inactive(), set())
