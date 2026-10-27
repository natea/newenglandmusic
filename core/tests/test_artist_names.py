from core.artist_matching import normalize
from core.artist_names import event_artist_names, name_parts, occasion_prefix
from core.models import Event
from django.test import SimpleTestCase


def names(title=None, artists=None, kind=""):
    return event_artist_names(Event(title=title, artists=artists, kind=kind))


class NormalizeTestCase(SimpleTestCase):
    def test_case_accents_punctuation_and_the(self):
        self.assertEqual(normalize("The Ballroom Thieves!"), "ballroom thieves")
        self.assertEqual(normalize("Beyoncé & Friends"), "beyonce and friends")
        self.assertEqual(normalize("Haven’s Den"), "havens den")

    def test_the_only_dropped_at_the_start(self):
        self.assertEqual(normalize("Theo and the Bridges"), "theo and the bridges")


class ArtistsTextTestCase(SimpleTestCase):
    def test_comma_separated_bill(self):
        self.assertEqual(
            names(artists="Arto Vaun, Shadow Monster, Dyr Faser"),
            ["Arto Vaun", "Shadow Monster", "Dyr Faser"],
        )

    def test_featuring_and_with(self):
        self.assertEqual(
            names(artists="Genevieve Artadi ft. Louis Cole w/ Chiquita Magic"),
            ["Genevieve Artadi", "Louis Cole", "Chiquita Magic"],
        )

    def test_leading_with_and_age_limits_removed(self):
        self.assertEqual(
            names(artists="with Jacyn Tremblay, Rhiannon Hurst (21+)"), ["Jacyn Tremblay", "Rhiannon Hurst"]
        )
        self.assertEqual(names(artists="Withered Hand (All Ages)"), ["Withered Hand"])
        self.assertEqual(names(artists="Armanii ( 18+ )"), ["Armanii"])

    def test_double_slashes(self):
        self.assertEqual(
            names(artists="Bomb Valley// Blesser //Seconds Before the Crash// Silvera"),
            ["Bomb Valley", "Blesser", "Seconds Before the Crash", "Silvera"],
        )
        self.assertEqual(names(title="AC/DC // Riot V"), ["AC/DC", "Riot V"])

    def test_joint_billing_and_set_notes(self):
        self.assertEqual(
            names(artists="Dead Poet Society x Honey Revenge, 49th & Main (DJ Set) (21+)"),
            ["Dead Poet Society", "Honey Revenge", "49th & Main"],
        )
        self.assertEqual(names(artists="Roni Size X Dieselboy"), ["Roni Size", "Dieselboy"])
        # an x inside a word, or ending a name, isn't a separator
        self.assertEqual(names(artists="Malcolm X, Xoth, The xx"), ["Malcolm X", "Xoth", "The xx"])
        # other notes in parentheses can be part of the name, or name another act
        self.assertEqual(names(artists="Andrea Neuenfeldt (of MK Naomi)"), ["Andrea Neuenfeldt (of MK Naomi)"])

    def test_ampersand_kept(self):
        self.assertEqual(
            names(artists="Simon & Garfunkel Story, Mumford & Sons"),
            ["Simon & Garfunkel Story", "Mumford & Sons"],
        )

    def test_other_separators(self):
        self.assertEqual(
            names(artists="Ana; Bo / Cy + Di featuring Ed feat. Flo"),
            ["Ana", "Bo", "Cy", "Di", "Ed", "Flo"],
        )


class TitleTestCase(SimpleTestCase):
    def test_headliner_only_in_the_title(self):
        self.assertEqual(
            names(
                title="SHEBAD w/ Psymon Spine + A Halloween Surprise",
                artists="SHEBAD, Psymon Spine",
            ),
            ["SHEBAD", "Psymon Spine", "A Halloween Surprise"],
        )

    def test_presenter_prefix_removed(self):
        result = names(title="State Theatre Presents: The Ballroom Thieves")
        self.assertIn("The Ballroom Thieves", result)
        self.assertNotIn("State Theatre", " ".join(result))

    def test_an_evening_with(self):
        self.assertEqual(names(title="An Evening With Lake Street Dive"), ["Lake Street Dive"])

    def test_tour_name_removed(self):
        self.assertEqual(
            names(title="GA-20 / Sue Foley: Together for the Holidays Tour (18+)"), ["GA-20", "Sue Foley"]
        )
        self.assertEqual(names(title="Blue October - 'Foiled' 20th Anniversary World Tour"), ["Blue October"])

    def test_show_name_after_a_dash_or_colon_dropped(self):
        self.assertEqual(names(title="Còig - early show"), ["Còig"])
        self.assertEqual(names(title="Corey Kent - Heartland Rock and Roll"), ["Corey Kent"])
        self.assertEqual(
            names(title="Dark Star Orchestra - Celebrating 45 Years of Reckoning"), ["Dark Star Orchestra"]
        )
        self.assertEqual(names(title="2hollis: The Pirouette Tour"), ["2hollis"])
        self.assertEqual(
            names(title="Connor Garvey & Ben Cosgrove — Together in Concert"), ["Connor Garvey & Ben Cosgrove"]
        )
        self.assertEqual(names(title="Akeem Ali -the Texture Tour"), ["Akeem Ali"])
        # in the artists text too
        self.assertEqual(names(artists="Còig - early show, Highway Kind"), ["Còig", "Highway Kind"])

    def test_dash_inside_a_name_kept(self):
        self.assertEqual(names(title="GA-20 + Jay-Z"), ["GA-20", "Jay-Z"])

    def test_openers_after_the_show_name_kept(self):
        self.assertEqual(
            names(title="Bumpin Uglies - Orange Crush Tour W/ Artikal Sound System, Joey Harkum"),
            ["Bumpin Uglies", "Artikal Sound System", "Joey Harkum"],
        )

    def test_tribute_only_in_the_show_name_keeps_the_band(self):
        self.assertEqual(names(title="Damn the Torpedoes - a Tribute To Tom Petty"), ["Damn the Torpedoes"])
        self.assertEqual(
            names(title='Damn the Torpedoes - "The Live Tom Petty Concert Experience"'), ["Damn the Torpedoes"]
        )

    def test_tribute_title_ignored(self):
        self.assertEqual(names(title="Dirty Deeds AC/DC Tribute", artists="Highway Kind"), ["Highway Kind"])
        self.assertEqual(names(title="Halloween Party w/ DJ Maltese"), ["DJ Maltese"])


class PlaceholderTestCase(SimpleTestCase):
    def test_placeholders(self):
        self.assertEqual(
            names(title="Fruition + Special Guests", artists="Organization"), ["Fruition"]
        )

    def test_other_placeholders(self):
        self.assertEqual(names(artists="TBA, tbd, DJ, X, and more, Special Guest"), [])

    def test_non_music_event(self):
        self.assertEqual(
            names(title="Lake Street Dive", artists="Highway Kind", kind=Event.Kind.OTHER), []
        )

    def test_unlabelled_event_counts_as_music(self):
        self.assertEqual(names(artists="Highway Kind"), ["Highway Kind"])


class DuoPartsTestCase(SimpleTestCase):
    def test_duo_split_into_acts(self):
        self.assertEqual(name_parts("Chris Collins & Boulder Canyon"), ["Chris Collins", "Boulder Canyon"])
        self.assertEqual(name_parts("Connor Garvey and Ben Cosgrove"), ["Connor Garvey", "Ben Cosgrove"])

    def test_one_word_parts_never_split(self):
        for name in ("Mumford & Sons", "Simon & Garfunkel", "Ax and the Hatchetmen", "Lake Street Dive"):
            self.assertEqual(name_parts(name), [], name)

    def test_backing_band_not_searched_on_its_own(self):
        self.assertEqual(name_parts("Chris Cote and his Band of These Guys"), ["Chris Cote"])


class OccasionPrefixTestCase(SimpleTestCase):
    artists = {"built to spill", "buffalo tom", "corey kent", "dark star"}

    def test_artist_then_occasion(self):
        self.assertEqual(occasion_prefix("built to spill fall 2026 tour", self.artists), "built to spill")
        self.assertEqual(occasion_prefix("buffalo tom 3rd annual charity concert", self.artists), "buffalo tom")
        self.assertEqual(
            occasion_prefix("corey kent heartland rock and roll tour", self.artists), "corey kent"
        )

    def test_rest_must_name_an_occasion(self):
        # "dark star orchestra" is another band, not an occasion of "dark star"
        self.assertIsNone(occasion_prefix("dark star orchestra", self.artists))

    def test_whole_name_isnt_its_own_prefix(self):
        self.assertIsNone(occasion_prefix("buffalo tom", self.artists))
