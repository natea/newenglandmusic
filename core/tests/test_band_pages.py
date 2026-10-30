import datetime
import os
from unittest import mock

from core.models import Artist, Band, BandMembership, Event, EventPerformer, Venue
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


def days(n):
    return timezone.now() + datetime.timedelta(days=n)


class BandPageTestCase(TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {"API_CONTACT_EMAIL": "contact@example.org"})
        env.start()
        self.addCleanup(env.stop)
        self.norwalk = Venue.objects.create(sheet_id="V1", name="District Music Hall", city_town="Norwalk", state="CT")
        self.portsmouth = Venue.objects.create(sheet_id="V2", name="3S Artspace", city_town="Portsmouth", state="NH")

    def band(self, **fields):
        return Band.objects.create(name=fields.pop("name", "Built To Spill"), **fields)

    def show(self, act, venue, when, approved=True, **fields):
        event = Event.all_objects.create(title="show", starttime=when, venue=venue, is_approved=approved, **fields)
        EventPerformer.objects.create(event=event, **({"band": act} if isinstance(act, Band) else {"artist": act}))
        return event

    def page(self, act):
        return self.client.get(act.get_absolute_url())

    def full_band(self):
        band = self.band(
            genres=["indie rock"], area="United States", begin_date="1992", website="https://builttospill.com/",
            bandcamp_url="https://built-to-spill.bandcamp.com/", instagram_url="https://www.instagram.com/builttospill/",
            youtube_url="https://www.youtube.com/channel/UCHx9idqEfLZjA2jxaXojccg", wikipedia_extract="Built to Spill is an American indie rock band.",
            wikipedia_url="https://en.wikipedia.org/wiki/Built_to_Spill", photo_file="Vegoose06 builttospill2 lg.jpg",
            photo_author="Joshrhinehart", photo_license="CC BY-SA 3.0", photo_license_url="https://creativecommons.org/licenses/by-sa/3.0/",
        )
        for name, begin, end in (("Doug Martsch", 1992, None), ("Melanie Radford", 2019, None), ("Brett Nelson", 1993, 2012)):
            BandMembership.objects.create(band=band, artist=Artist.objects.create(name=name), begin_year=begin, end_year=end)
        self.show(band, self.norwalk, days(3))
        self.show(band, self.portsmouth, days(7))
        return band

    def test_a_band_with_everything(self):
        html = self.page(self.full_band()).content.decode()
        for text in (
            '<h1 class="act-tab" id="act-name">Built To Spill</h1>', "Band · indie rock · United States · since 1992",
            "act-next", "Doug Martsch", "Former members", ">Website<", ">Bandcamp<", ">Instagram<", ">YouTube<",
            "Special:FilePath/Vegoose06_builttospill2_lg.jpg?width=640", "Built to Spill is an American indie rock band.",
            "Upcoming shows",
        ):
            self.assertIn(text, html)
        self.assertNotIn("Send us a photo", html)

    def test_a_band_with_only_a_name_and_shows(self):
        band = self.band(name="Zipper")
        self.show(band, self.norwalk, days(3))
        html = self.page(band).content.decode()
        for missing in ("<dt>Members</dt>", "<dt>Links</dt>", "<dt>Photo</dt>", "act-bio", "act-fields"):
            self.assertNotIn(missing, html)
        self.assertIn("Send us a photo, bio or links", html)
        self.assertIn("District Music Hall", html)

    def test_unknown_band(self):
        self.assertEqual(self.client.get("/bands/no-such-band").status_code, 404)
        self.assertEqual(self.client.get("/artists/no-such-artist").status_code, 404)

    def test_next_show_and_the_rest(self):
        response = self.page(self.full_band())
        html = response.content.decode()
        nxt = html[html.index('class="act-next"'):html.index("</p>", html.index('class="act-next"'))]
        self.assertIn("District Music Hall", nxt)
        self.assertIn("Norwalk, CT", nxt)
        self.assertIn("1 more show", nxt)
        self.assertEqual([e.venue.name for e in response.context["shows"]], ["District Music Hall", "3S Artspace"])

    def test_no_upcoming_shows(self):
        band = self.band()
        self.show(band, self.norwalk, days(-10))
        response = self.page(band)
        self.assertIn("No upcoming shows listed.", response.content.decode())
        self.assertEqual(response.context["shows"], [])
        # a thin page stays out of search results
        self.assertIn('<meta name="robots" content="noindex">', response.content.decode())

    def test_unapproved_events(self):
        band = self.band()
        self.show(band, self.norwalk, days(3), approved=False)
        self.assertEqual(self.page(band).context["shows"], [])

    def test_current_and_former_members(self):
        response = self.page(self.full_band())
        self.assertEqual([a.name for a, *_ in response.context["current_members"]], ["Doug Martsch", "Melanie Radford"])
        self.assertEqual([(a.name, y) for a, _, y, _ in response.context["former_members"]], [("Brett Nelson", "1993–2012")])
        self.assertIn("since 1992", response.content.decode())

    def test_an_artists_bands(self):
        kim = Artist.objects.create(name="Kim Deal")
        pixies, breeders = self.band(name="Pixies"), self.band(name="The Breeders")
        BandMembership.objects.create(band=pixies, artist=kim, role="bass", begin_year=1986, end_year=2013)
        BandMembership.objects.create(band=breeders, artist=kim, role="vocals", begin_year=1989)
        html = self.page(kim).content.decode()
        self.assertIn("<dt>Bands</dt>", html)
        self.assertIn(f'href="{pixies.get_absolute_url()}"', html)
        self.assertIn(f'href="{breeders.get_absolute_url()}"', html)
        self.assertLess(html.index("The Breeders"), html.index("Pixies</a>"))

    def test_some_links(self):
        band = self.band(website="https://example.com/", bandcamp_url="https://x.bandcamp.com/")
        html = self.page(band).content.decode()
        self.assertIn(">Website<", html)
        self.assertIn(">Bandcamp<", html)
        self.assertNotIn(">Instagram<", html)
        self.assertNotIn(">YouTube<", html)

    def test_a_credited_photo(self):
        band = self.band(name="Bonerama", photo_file="Bonerama2006.jpg", photo_author="Masahiro Sumori", photo_license="CC BY-SA 3.0",
                         photo_license_url="https://creativecommons.org/licenses/by-sa/3.0/")
        html = self.page(band).content.decode()
        self.assertIn('<img src="https://commons.wikimedia.org/wiki/Special:FilePath/Bonerama2006.jpg?width=640" alt="Bonerama">', html)
        self.assertIn("Photo: Masahiro Sumori,", html)
        self.assertIn('href="https://creativecommons.org/licenses/by-sa/3.0/"', html)
        self.assertIn('href="https://commons.wikimedia.org/wiki/File:Bonerama2006.jpg"', html)

    def test_no_free_photo(self):
        self.assertNotIn("<dt>Photo</dt>", self.page(self.band()).content.decode())

    def test_wikipedia_bio(self):
        html = self.page(self.full_band()).content.decode()
        self.assertIn('From the Wikipedia article <a href="https://en.wikipedia.org/wiki/Built_to_Spill"', html)
        self.assertIn('href="https://creativecommons.org/licenses/by-sa/4.0/"', html)

    def test_only_a_disambiguation_note(self):
        html = self.page(self.band(name="Krill", disambiguation="Boston indie rock band")).content.decode()
        self.assertIn("Boston indie rock band.", html)
        self.assertNotIn("Wikipedia", html)

    def test_genres_are_credited(self):
        html = self.page(self.band(genres=["punk"], musicbrainz_id="11111111-1111-4111-8111-111111111111")).content.decode()
        self.assertIn("Genres from <a", html)
        self.assertIn("CC BY-NC-SA", html)

    def test_the_invitation(self):
        band = self.band(name="Krill")
        html = self.page(band).content.decode()
        self.assertIn('href="mailto:contact@example.org?subject=Krill%20on%20', html)

    def test_title_and_image_text(self):
        html = self.page(self.full_band()).content.decode()
        self.assertIn("<title>Built To Spill | New England Music</title>", html)
        self.assertIn('alt="Built To Spill"', html)


class LinksFromTheCalendarTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V1", name="Paradise", city_town="Boston", state="MA")
        self.pixies = Band.objects.create(name="Pixies")

    def test_a_linked_performer(self):
        from core.event_performers import link_from_names

        event = Event.all_objects.create(title="show", artists="Pixies, Dana and Alden", starttime=days(3), venue=self.venue,
                                         hyperlink="https://venue.example/show")
        link_from_names(event)
        html = Event.all_objects.get(pk=event.pk).baked_html_template
        self.assertIn('<a class="performer" href="/bands/pixies">Pixies</a>, Dana and Alden', html)
        # the event's own link covers only its title now
        self.assertIn("<a href=\"https://venue.example/show\" target=\"_blank\"><span class='artist-present'>show:", html)

    def test_names_that_arent_performers_stay_plain(self):
        event = Event.all_objects.create(title="show", artists="Dana and Alden", starttime=days(3), venue=self.venue)
        html = Event.all_objects.get(pk=event.pk).baked_html_template
        self.assertNotIn('class="performer"', html)
        self.assertIn('<span class="artists">Dana and Alden</span>', html)

    def test_unlinking_rerenders(self):
        from core.event_performers import link_from_names

        event = Event.all_objects.create(title="show", artists="Pixies", starttime=days(3), venue=self.venue)
        link_from_names(event)
        self.pixies.delete()
        link_from_names(event)
        self.assertNotIn('class="performer"', Event.all_objects.get(pk=event.pk).baked_html_template)

    def test_sitemap_lists_acts_with_upcoming_shows(self):
        from core.event_performers import link_from_names

        Band.objects.create(name="Krill")
        event = Event.all_objects.create(title="show", artists="Pixies", starttime=days(3), venue=self.venue, is_approved=True)
        link_from_names(event)
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/bands/pixies", xml)
        self.assertNotIn("/bands/krill", xml)


class ArtistMetaTestCase(TestCase):
    def test_a_persons_birth_year_isnt_shown_as_since(self):
        kim = Artist.objects.create(name="Kim Deal", city_town="Dayton", state="OH", begin_date="1961-06-10")
        html = self.client.get(kim.get_absolute_url()).content.decode()
        self.assertIn("Artist · Dayton, OH", html)
        self.assertNotIn("since 1961", html)


class FinishFixesTestCase(TestCase):
    """the finish review's fixes (2026-10-29)"""

    # the page tests' venues and helpers, without their tests
    setUp, band, show, page, full_band = (
        BandPageTestCase.setUp, BandPageTestCase.band, BandPageTestCase.show, BandPageTestCase.page, BandPageTestCase.full_band,
    )

    def test_shows_carry_the_calendars_save_and_calendar_actions(self):
        band = self.full_band()
        html = self.page(band).content.decode()
        event_ids = [e.pk for e in Event.objects.filter(performers__band=band)]
        for pk in event_ids:
            self.assertIn(f'action="/saved/toggle/{pk}"', html)
            self.assertIn(f'href="/event/{pk}/ics"', html)
        self.assertIn(f'id="event-{event_ids[0]}"', html)

    def test_one_show_isnt_listed_twice(self):
        band = self.band()
        self.show(band, self.norwalk, days(3))
        html = self.page(band).content.decode()
        self.assertIn("act-next", html)
        self.assertNotIn("Upcoming shows", html)

    def test_former_members_past_three_fold(self):
        band = self.band()
        for i in range(6):
            BandMembership.objects.create(band=band, artist=Artist.objects.create(name=f"Former {i}"), begin_year=1990 + i, end_year=2000 + i)
        response = self.page(band)
        self.assertEqual(len(response.context["former_members"]), 3)
        self.assertIn("<summary>3 more former members</summary>", response.content.decode())

    def test_four_former_members_dont_fold_one(self):
        band = self.band()
        for i in range(4):
            BandMembership.objects.create(band=band, artist=Artist.objects.create(name=f"Former {i}"), end_year=2000)
        self.assertNotIn("<summary>", self.page(band).content.decode())

    def test_the_wikipedia_credit_names_the_article(self):
        html = self.page(self.full_band()).content.decode()
        self.assertIn('rel="noopener" target="_blank">Built to Spill</a>, under', html)

    def test_headshots_have_empty_alt_beside_the_named_link(self):
        band = self.band()
        kim = Artist.objects.create(name="Kim Deal", photo_file="Kim Deal Smoke.jpg", photo_license="CC BY 2.0")
        BandMembership.objects.create(band=band, artist=kim, begin_year=1986)
        BandMembership.objects.create(band=band, artist=Artist.objects.create(name="Joey Santiago"), begin_year=1986)
        html = self.page(band).content.decode()
        self.assertIn('alt="" width="48" height="48"', html)
        # the member without a headshot keeps the column
        self.assertIn('<span class="act-headshot-slot"></span>', html)


class ShowTimesTestCase(TestCase):
    setUp, band, show, page = BandPageTestCase.setUp, BandPageTestCase.band, BandPageTestCase.show, BandPageTestCase.page

    def test_each_row_has_its_time(self):
        band = self.band()
        when = timezone.localtime(days(5)).replace(hour=19, minute=0)
        self.show(band, self.norwalk, when)
        self.show(band, self.norwalk, when.replace(hour=22))
        html = self.page(band).content.decode()
        self.assertIn('<span class="act-show-time">7:00 p.m.</span>', html)
        self.assertIn('<span class="act-show-time">10:00 p.m.</span>', html)
