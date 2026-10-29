from core.management.commands.match_ticketmaster_venues import MAX_DISTANCE_KM, find_match
from core.models import Venue
from core.venue_matching import distance_km, names_match, normalize_name, spelling_variants
from django.test import SimpleTestCase

PARADISE = (42.35183, -71.11954)


def candidate(id, name, lat=None, lon=None):
    return {"id": id, "name": name, "address": "", "city": "", "state": "", "latitude": lat, "longitude": lon}


class NameMatchingTestCase(SimpleTestCase):
    def test_matching_names(self):
        for ours, theirs in (
            ("Paradise Rock Club", "Paradise Rock Club presented by Citizens"),
            ("MGM Music Hall", "MGM Music Hall at Fenway"),
            ("The Orpheum Theatre", "Orpheum Theater"),
            ("9:30 Club", "9:30 Club"),
            ("Empire Live / Empire Underground", "Empire Live"),
            ("Mr. Smalls", "Mr Smalls Theatre"),
        ):
            self.assertTrue(names_match(ours, theirs), (ours, theirs))

    def test_different_names(self):
        for ours, theirs in (
            ("Paradise Rock Club", "Paradise City Bar"),
            ("Big Night Live", "Big Nightclub"),
            ("Reverb", "Reverberation Room"),
        ):
            self.assertFalse(names_match(ours, theirs), (ours, theirs))

    def test_contained_name_matches_so_distance_decides(self):
        # names are matched loosely; the distance check keeps this from linking
        self.assertTrue(names_match("The Sinclair", "Sinclair Oil Arena"))
        outcome, _, _ = find_match(
            Venue(name="The Sinclair", latitude=42.3734, longitude=-71.1210),
            [candidate("a", "Sinclair Oil Arena", 41.0, -73.0)],
        )
        self.assertEqual(outcome, "ambiguous")

    def test_name_of_only_noise_words_still_compares(self):
        self.assertEqual(normalize_name("The Club"), "the club")
        self.assertTrue(names_match("The Club", "The Club"))

    def test_apostrophes_and_add_on_words(self):
        self.assertTrue(names_match("Fast Eddie's Billiards", "Fast Eddies Billiards Cafe"))

    def test_apostrophe_inside_a_word(self):
        self.assertTrue(names_match("Shayna B's By The Sea", "Shayna Bs By The Sea"))
        self.assertTrue(names_match("O'Brien's", "O’Briens Pub"))
        self.assertTrue(names_match("O'Brien's", "O'Briens Pub"))

    def test_accents(self):
        self.assertTrue(names_match("Cultured Cafe", "The Remedy's Cultured Café"))

    def test_street_abbreviations(self):
        self.assertTrue(names_match("25 Central Street", "25 Central St"))
        self.assertTrue(names_match("Main Ave Pub", "Main Avenue"))

    def test_trailing_parenthetical(self):
        self.assertTrue(names_match("Gametime Lanes", "Gametime Lanes & Entertainment (Amesbury Location)"))
        # a name that's only a parenthetical keeps it
        self.assertEqual(normalize_name("(Le Poisson Rouge)"), "le poisson rouge")

    def test_different_places_still_differ(self):
        for ours, theirs in (
            ("Bleacher's Bar", "The Midway"),
            ("Thompson Speedway", "Thompson Raceway"),
            # "bar" goes only as a whole word
            ("Barcade", "Arcade"),
        ):
            self.assertFalse(names_match(ours, theirs), (ours, theirs))

    def test_distance_km(self):
        # paradise rock club to the orpheum, about 4.5 km
        self.assertAlmostEqual(distance_km(*PARADISE, 42.3558, -71.0610), 4.83, places=1)
        self.assertEqual(distance_km(*PARADISE, *PARADISE), 0)
        self.assertIsNone(distance_km(*PARADISE, None, None))


class SpellingVariantsTestCase(SimpleTestCase):
    def test_theater_and_theatre(self):
        self.assertEqual(spelling_variants("The State Theater"), ["The State Theater", "The State Theatre"])
        self.assertEqual(spelling_variants("Lincoln THEATRE"), ["Lincoln THEATRE", "Lincoln THEATer"])
        self.assertEqual(spelling_variants("Theatrestuff Hall"), ["Theatrestuff Hall"])
        self.assertEqual(spelling_variants("Paradise Rock Club"), ["Paradise Rock Club"])
