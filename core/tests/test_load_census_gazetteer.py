from io import StringIO

from core.management.commands.load_census_gazetteer import strip_suffix
from core.models import CensusPlace
from core.tests.census_fixture import FakeCensus
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase


class LoadTestCase(TestCase):
    def run_command(self, census, *args):
        out = StringIO()
        with census.patch():
            call_command("load_census_gazetteer", *args, stdout=out)
        return out.getvalue()

    def test_loading_the_data(self):
        CensusPlace.objects.create(kind="town", name="Old", state="MA", search_key="old", latitude=0, longitude=0)
        census = FakeCensus()
        out = self.run_command(census, "--year", "2026")
        self.assertIn("3 zip code areas and 10 towns", out)
        self.assertFalse(CensusPlace.objects.filter(name="Old").exists())
        somerville = CensusPlace.objects.get(kind="town", name="Somerville", state="MA")
        self.assertEqual((somerville.search_key, somerville.latitude), ("somerville", 42.390445))
        self.assertEqual(CensusPlace.objects.get(kind="zip", name="02144").longitude, -71.123088)
        # a town and a place of the same name and state are stored once, the town first
        johnson = CensusPlace.objects.get(name="Johnson", state="VT")
        self.assertEqual(johnson.latitude, 44.648124)
        self.assertTrue(CensusPlace.objects.filter(name="Brooklyn Heights", state="NY").exists())
        self.assertTrue(all("2026_Gazetteer" in url for url in census.requests))

    def test_download_fails(self):
        CensusPlace.objects.create(kind="town", name="Old", state="MA", search_key="old", latitude=0, longitude=0)
        with self.assertRaises(CommandError):
            self.run_command(FakeCensus(failing="place_national"))
        self.assertEqual(list(CensusPlace.objects.values_list("name", flat=True)), ["Old"])


class SuffixTestCase(SimpleTestCase):
    def test_strip_suffix(self):
        for name, expected in (
            ("Somerville city", "Somerville"), ("Hamden town", "Hamden"), ("Brooklyn Heights CDP", "Brooklyn Heights"),
            ("Springfield township", "Springfield"), ("Town", "Town"), ("Warren Gore", "Warren"), ("Boston", "Boston"),
        ):
            with self.subTest(name):
                self.assertEqual(strip_suffix(name), expected)
