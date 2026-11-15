from pathlib import Path

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core import link_hubs
from core.models import Artist, Band

FIXTURES = Path(__file__).parent / "fixtures" / "link_hubs"


def page(name):
    return (FIXTURES / name).read_text()


def applied(record, links):
    return link_hubs.apply(record, links, timezone.now())


class HubAddressTests(SimpleTestCase):
    def test_a_page_on_a_hub(self):
        self.assertEqual(link_hubs.hub_for("https://linktr.ee/sunnydaze").name, "Linktree")
        self.assertEqual(link_hubs.hub_for("https://www.beacons.ai/krillband").name, "Beacons")

    def test_not_a_page_on_a_hub(self):
        for url in ("https://linktr.ee/", "https://linktr.ee", "https://linktr.ee/login", "https://example.com/links", "", "ftp://linktr.ee/a"):
            self.assertIsNone(link_hubs.hub_for(url), url)
            self.assertEqual(link_hubs.clean_hub_url(url), "")

    def test_a_hub_address_is_stored_as_https_without_a_query(self):
        self.assertEqual(link_hubs.clean_hub_url("http://LINKTR.ee/sunnydaze?utm=1#x"), "https://linktr.ee/sunnydaze")

    def test_the_same_address_written_differently(self):
        self.assertTrue(link_hubs.same_address("https://instagram.com/krill.band", "https://www.instagram.com/Krill.Band/?hl=en"))
        self.assertFalse(link_hubs.same_address("https://instagram.com/krill", "https://instagram.com/krill.band"))


class ReadingLinksTests(SimpleTestCase):
    def test_links_from_embedded_json(self):
        urls = [url for _, url in link_hubs.links_on(page("linktree.html"))]
        self.assertIn("https://krill.bandcamp.com/", urls)
        self.assertEqual(len(urls), len(set(urls)))

    def test_links_from_anchors_with_their_labels(self):
        found = dict((url, label) for label, url in link_hubs.links_on(page("anchors.html")))
        self.assertEqual(found["https://sunnydaze.com"], "Official website")
        self.assertNotIn("/login", found)

    def test_a_page_with_no_links(self):
        self.assertEqual(link_hubs.links_on(page("empty.html")), [])
        self.assertFalse(link_hubs.has_script(page("empty.html")))

    def test_a_page_whose_links_are_built_by_script(self):
        self.assertEqual(link_hubs.links_on(page("scripted.html")), [])
        self.assertTrue(link_hubs.has_script(page("scripted.html")))

    def test_embedded_data_is_not_a_script_that_builds_links(self):
        self.assertFalse(link_hubs.has_script(page("linktree.html")))


class ClassifyTests(SimpleTestCase):
    def test_a_readable_page(self):
        found = link_hubs.classify(link_hubs.links_on(page("linktree.html")))
        self.assertEqual(found["bandcamp_url"], ["https://krill.bandcamp.com/"])
        self.assertEqual(found["instagram_url"], ["https://www.instagram.com/krill.band/"])
        self.assertEqual(found["youtube_url"], ["https://www.youtube.com/channel/UC123"])
        self.assertEqual(found["website"], [])

    def test_a_video_is_not_a_channel(self):
        found = link_hubs.classify([("Video", "https://www.youtube.com/watch?v=abc123"), ("Playlist", "https://www.youtube.com/playlist?list=a"), ("Short", "https://youtu.be/abc")])
        self.assertEqual(found["youtube_url"], [])

    def test_youtube_handles_and_channels(self):
        found = link_hubs.classify([("", "https://www.youtube.com/@krill"), ("", "https://youtube.com/c/krill")])
        self.assertEqual(len(found["youtube_url"]), 2)

    def test_an_instagram_post_is_not_a_profile(self):
        found = link_hubs.classify([("", "https://www.instagram.com/p/abc/"), ("", "http://www.instagram.com/krill")])
        self.assertEqual(found["instagram_url"], [])

    def test_the_hubs_own_label_names_the_website(self):
        found = link_hubs.classify([("Official website", "https://krillband.com")])
        self.assertEqual(found["website"], ["https://krillband.com"])

    def test_a_link_on_another_site(self):
        self.assertEqual(link_hubs.classify([("", "https://example.com/shop")])["website"], [])
        self.assertEqual(link_hubs.classify([("Merch", "https://example.com/shop")])["website"], [])

    def test_a_social_site_is_not_the_website(self):
        found = link_hubs.classify([("Official Facebook", "https://facebook.com/krill"), ("Official site", "https://linktr.ee/krill")])
        self.assertEqual(found["website"], [])

    def test_not_a_bandcamp_address(self):
        self.assertEqual(link_hubs.classify([("Bandcamp", "https://example.com/music")])["bandcamp_url"], [])

    def test_an_address_too_long_for_its_field(self):
        long = "https://www.instagram.com/" + "a" * 300
        self.assertEqual(link_hubs.classify([("", long)])["instagram_url"], [])
        self.assertEqual(link_hubs.classify([("Website", "https://example.com/" + "a" * 200)])["website"], [])

    def test_the_same_link_twice_is_one_candidate(self):
        found = link_hubs.classify([("", "https://www.instagram.com/krill.band/"), ("", "https://instagram.com/krill.band?hl=en")])
        self.assertEqual(len(found["instagram_url"]), 1)


class ApplyTests(TestCase):
    INSTAGRAM = ("Instagram", "https://www.instagram.com/krill.band/")

    def test_filling_an_empty_field(self):
        band = Band.objects.create(name="Krill")
        changes, findings = applied(band, [self.INSTAGRAM])
        self.assertEqual(changes, {"instagram_url": "https://www.instagram.com/krill.band/"})
        self.assertEqual(findings, [])

    def test_several_candidates(self):
        band = Band.objects.create(name="Krill")
        changes, findings = applied(band, [self.INSTAGRAM, ("Other", "https://www.instagram.com/krill.too/")])
        self.assertEqual(changes, {})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["field"], "instagram_url")
        self.assertEqual(len(findings[0]["options"]), 2)

    def test_protected_values_stay(self):
        for source in ("editor", "import", "musicbrainz", "wikidata"):
            band = Band.objects.create(
                name=f"Krill {source}", website="https://old.example.com", field_sources={"website": source}
            )
            changes, findings = applied(band, [("Website", "https://krillband.com")])
            self.assertEqual(changes, {}, source)
            self.assertEqual((findings[0]["current"], findings[0]["hub"]), ("https://old.example.com", "https://krillband.com"))

    def test_a_hub_address_in_the_website_field(self):
        artist = Artist.objects.create(
            name="Sunny Daze", website="https://linktr.ee/sunnydaze", field_sources={"website": "import"}
        )
        changes, findings = applied(artist, [("Website", "https://sunnydaze.com")])
        self.assertEqual(changes, {})
        self.assertEqual((findings[0]["field"], findings[0]["current"], findings[0]["hub"]), ("website", "https://linktr.ee/sunnydaze", "https://sunnydaze.com"))

    def test_a_conflicting_youtube_link(self):
        band = Band.objects.create(name="Krill", youtube_url="https://www.youtube.com/@krill", field_sources={"youtube_url": "editor"})
        changes, findings = applied(band, [("YouTube", "https://www.youtube.com/channel/UC123")])
        self.assertEqual(changes, {})
        self.assertEqual(findings[0]["current"], "https://www.youtube.com/@krill")
        self.assertEqual(findings[0]["hub"], "https://www.youtube.com/channel/UC123")

    def test_the_same_address_written_differently(self):
        band = Band.objects.create(name="Krill", instagram_url="https://instagram.com/krill.band", field_sources={"instagram_url": "editor"})
        changes, findings = applied(band, [("Instagram", "https://www.instagram.com/Krill.Band/?hl=en")])
        self.assertEqual((changes, findings), ({}, []))

    def test_a_finding_goes_away(self):
        band = Band.objects.create(name="Krill", youtube_url="https://www.youtube.com/channel/UC123", field_sources={"youtube_url": "editor"})
        band.link_hub_findings = [{"field": "youtube_url", "current": "https://www.youtube.com/@krill", "hub": "https://www.youtube.com/channel/UC123", "seen_at": "2026-11-01T00:00:00+00:00", "dismissed": False}]
        self.assertEqual(applied(band, [("YouTube", "https://www.youtube.com/channel/UC123")])[1], [])

    def test_a_finding_goes_away_when_the_hub_drops_the_link(self):
        band = Band.objects.create(name="Krill", youtube_url="https://www.youtube.com/@krill")
        band.link_hub_findings = [{"field": "youtube_url", "current": band.youtube_url, "hub": "https://www.youtube.com/channel/UC123", "seen_at": "x", "dismissed": False}]
        self.assertEqual(applied(band, [self.INSTAGRAM])[1], [])

    def test_a_finding_is_replaced_by_a_new_hub_value(self):
        band = Band.objects.create(name="Krill", youtube_url="https://www.youtube.com/@krill")
        band.link_hub_findings = [{"field": "youtube_url", "current": band.youtube_url, "hub": "https://www.youtube.com/channel/OLD", "seen_at": "x", "dismissed": False}]
        findings = applied(band, [("YouTube", "https://www.youtube.com/channel/NEW")])[1]
        self.assertEqual([f["hub"] for f in findings], ["https://www.youtube.com/channel/NEW"])

    def test_a_dismissed_finding(self):
        band = Band.objects.create(name="Krill", youtube_url="https://www.youtube.com/@krill")
        dismissed = {"field": "youtube_url", "current": band.youtube_url, "hub": "https://www.youtube.com/channel/UC123", "seen_at": "x", "dismissed": True}
        band.link_hub_findings = [dismissed]
        changes, findings = applied(band, [("YouTube", "https://www.youtube.com/channel/UC123")])
        self.assertEqual(findings, [dismissed])
        # a different hub value is a new finding
        findings = applied(band, [("YouTube", "https://www.youtube.com/channel/UC999")])[1]
        self.assertEqual([f["dismissed"] for f in findings], [True, False])

    def test_a_changed_hub_replaces_its_own_fill(self):
        band = Band.objects.create(name="Krill", instagram_url="https://www.instagram.com/old/", field_sources={"instagram_url": "link hub"})
        changes, findings = applied(band, [self.INSTAGRAM])
        self.assertEqual(changes, {"instagram_url": "https://www.instagram.com/krill.band/"})
        self.assertEqual(findings, [])

    def test_a_fill_the_hub_no_longer_links_stays(self):
        band = Band.objects.create(name="Krill", instagram_url="https://www.instagram.com/old/", field_sources={"instagram_url": "link hub"})
        self.assertEqual(applied(band, []), ({}, []))

    def test_several_candidates_do_not_replace_a_hub_fill(self):
        band = Band.objects.create(name="Krill", instagram_url="https://www.instagram.com/old/", field_sources={"instagram_url": "link hub"})
        changes, findings = applied(band, [self.INSTAGRAM, ("", "https://www.instagram.com/krill.too/")])
        self.assertEqual(changes, {})
        self.assertEqual(len(findings), 1)
