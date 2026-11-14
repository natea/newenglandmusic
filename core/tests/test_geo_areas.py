from collections import Counter

from django.test import SimpleTestCase
from django.utils.text import slugify

from core.geo_areas import AREAS, OLD_METRO_SLUGS

# every county in massachusetts, as venues spell them (lowercased)
MASSACHUSETTS_COUNTIES = {
    "barnstable", "berkshire", "bristol", "dukes", "essex", "franklin", "hampden", "hampshire", "middlesex",
    "nantucket", "norfolk", "plymouth", "suffolk", "worcester",
}


def sub_regions():
    return [area for area in AREAS if area["group"]]


class GeoAreasDataTestCase(SimpleTestCase):
    def test_every_sub_region_is_complete(self):
        self.assertEqual(len(sub_regions()), 28)
        for area in sub_regions():
            with self.subTest(area["key"]):
                self.assertEqual((area["kind"], area["home_state"], area["states"]), ("metro", "MA", ["ma"]))
                self.assertTrue(area["label"].startswith("MA: "))
                self.assertTrue(area["cities"] or area["neighborhoods"])

    def test_seven_groups_in_order(self):
        groups = list(dict.fromkeys(area["group"] for area in sub_regions()))
        self.assertEqual(
            groups,
            [
                "Western Massachusetts", "Central Massachusetts", "MetroWest", "Greater Boston",
                "Northeast Massachusetts", "South of Boston & Southeast", "Cape Cod & the Islands",
            ],
        )

    def test_each_county_has_exactly_one_default(self):
        defaults = Counter(county for area in sub_regions() for county in area["default_counties"])
        self.assertEqual(set(defaults), MASSACHUSETTS_COUNTIES)
        self.assertEqual({count for count in defaults.values()}, {1})

    def test_no_town_in_two_sub_regions(self):
        # a venue's town places it in exactly one sub-region, so no town may be listed twice
        towns = Counter(town for area in sub_regions() for town in area["cities"])
        self.assertEqual([town for town, count in towns.items() if count > 1], [])
        neighborhoods = Counter(name for area in sub_regions() for name in area["neighborhoods"])
        self.assertEqual([name for name, count in neighborhoods.items() if count > 1], [])

    def test_matching_lists_are_lowercase(self):
        for area in AREAS:
            for field in ("states", "counties", "cities", "neighborhoods", "default_counties"):
                with self.subTest(area["key"], field=field):
                    self.assertEqual(area[field], [value.lower() for value in area[field]])

    def test_aliases(self):
        towns = {town: area["label"] for area in sub_regions() for town in area["cities"]}
        for town in ("allston", "brighton"):
            self.assertEqual(towns[town], "MA: Boston Neighborhoods")
        for town in ("barnstable", "hyannis"):
            self.assertEqual(towns[town], "MA: Mid-Cape")
        for town in ("tisbury", "vineyard haven"):
            self.assertEqual(towns[town], "MA: Martha's Vineyard")
        for town in ("gosnold", "cuttyhunk"):
            self.assertEqual(towns[town], "MA: Elizabeth Islands")
        for town in ("manchester-by-the-sea", "manchester"):
            self.assertEqual(towns[town], "MA: Cape Ann")
        neighborhoods = {name: area["label"] for area in sub_regions() for name in area["neighborhoods"]}
        for name in ("fenway", "fenway-kenmore", "downtown", "downtown crossing"):
            self.assertEqual(neighborhoods[name], "MA: Downtown & Central Boston")

    def test_keys_and_slugs_unique(self):
        self.assertEqual(len({area["key"] for area in AREAS}), len(AREAS))
        slugs = [(area["kind"], slugify(area["label"])) for area in AREAS]
        self.assertEqual(len(set(slugs)), len(slugs))
        self.assertIn(("metro", "ma-north-of-the-charles"), slugs)
        self.assertIn(("metro", "ma-downtown-central-boston"), slugs)

    def test_old_metro_slugs_are_gone(self):
        # an old slug must not name a new area, or it would never fall back to massachusetts
        self.assertEqual(len(OLD_METRO_SLUGS), 6)
        slugs = {slugify(area["label"]) for area in AREAS}
        self.assertEqual(OLD_METRO_SLUGS & slugs, set())
