from datetime import timedelta

from core.calendar_feeds import event_uid
from core.geo_filters import COOKIE_NAME as GEO_COOKIE
from core.models import Event, GeoArea, Venue
from core.tests.geo_fixture import load_geo_fixture
from django.test import TestCase, override_settings
from django.utils import timezone
from icalendar import Calendar


def parse(response):
    return Calendar.from_ical(response.content)


def summaries(response):
    return [str(entry["SUMMARY"]) for entry in parse(response).walk("VEVENT")]


# the defaults, whatever SITE_NAME and UID_DOMAIN a developer's .env sets
DEFAULTS = override_settings(SITE_NAME="New England Music", UID_DOMAIN="newenglandmusic")


@DEFAULTS
class SingleEventDownloadTestCase(TestCase):
    def setUp(self):
        self.event = Event.objects.create(title="a show", starttime=timezone.now() + timedelta(days=2))

    def entry(self):
        return parse(self.client.get(f"/event/{self.event.pk}/ics")).walk("VEVENT")[0]

    def test_same_uid_on_every_download(self):
        self.assertEqual(str(self.entry()["UID"]), event_uid(self.event))
        self.assertEqual(str(self.entry()["UID"]), str(self.entry()["UID"]))

    def test_uid_doesnt_depend_on_the_sites_address(self):
        with self.settings(SITE_URL="https://newenglandmusic.example"):
            self.assertEqual(event_uid(self.event), f"event-{self.event.pk}@newenglandmusic")

    def test_uid_domain_from_the_settings(self):
        with self.settings(UID_DOMAIN="boston-shows"):
            self.assertEqual(str(self.entry()["UID"]), f"event-{self.event.pk}@boston-shows")

    def test_link_and_times(self):
        entry = self.entry()
        self.assertTrue(str(entry["URL"]).endswith(f"/event/{self.event.pk}"))
        self.assertEqual(entry["DTEND"].dt - entry["DTSTART"].dt, timedelta(hours=1))
        self.assertNotIn("STATUS", entry)

    def test_cancelled(self):
        self.event.is_cancelled = True
        self.event.save()
        self.assertEqual(str(self.entry()["STATUS"]), "CANCELLED")


@DEFAULTS
class FeedTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        self.now = timezone.now()
        self.venues = {}
        for city, state, county in [
            ("Boston", "MA", "Suffolk"),
            ("Hyannis", "MA", "Barnstable"),
            ("Burlington", "VT", "Chittenden"),
            ("Providence", "RI", "Providence"),
        ]:
            self.venues[city] = Venue.objects.create(name=f"{city} venue", state=state, county=county, city_town=city)

    def show(self, title, city, days=3, **fields):
        return Event.objects.create(
            title=title, starttime=self.now + timedelta(days=days), venue=self.venues[city], **fields
        )

    def slug(self, label):
        return GeoArea.objects.get(label=label).slug

    def test_state_feed(self):
        self.show("burlington show", "Burlington")
        self.show("boston show", "Boston")
        response = self.client.get("/calendar.ics?state=" + self.slug("Vermont"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertEqual(summaries(response), ["burlington show [New England Music]"])

    def test_metro_feed(self):
        self.show("boston show", "Boston")
        self.show("cape show", "Hyannis")
        response = self.client.get("/calendar.ics?metro=" + self.slug("MA: Boston"))
        self.assertEqual(summaries(response), ["boston show [New England Music]"])

    def test_whole_northeast(self):
        for city in ("Boston", "Hyannis", "Burlington", "Providence"):
            self.show(f"{city} show", city)
        self.assertEqual(len(summaries(self.client.get("/calendar.ics"))), 4)

    def test_remembered_filter_ignored(self):
        self.show("burlington show", "Burlington")
        self.client.cookies[GEO_COOKIE] = "state=" + self.slug("Massachusetts")
        response = self.client.get("/calendar.ics?state=" + self.slug("Vermont"))
        self.assertEqual(summaries(response), ["burlington show [New England Music]"])
        self.assertNotIn(GEO_COOKIE, response.cookies)

    def test_unknown_area(self):
        self.show("boston show", "Boston")
        self.show("burlington show", "Burlington")
        response = self.client.get("/calendar.ics?state=atlantis")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(summaries(response)), 2)

    def test_stable_identifiers(self):
        show = self.show("boston show", "Boston")
        uids = [str(parse(self.client.get("/calendar.ics")).walk("VEVENT")[0]["UID"]) for _ in range(2)]
        download = parse(self.client.get(f"/event/{show.pk}/ics")).walk("VEVENT")[0]
        self.assertEqual(uids, [str(download["UID"])] * 2)

    def test_cancelled_event(self):
        self.show("cancelled show", "Boston", is_cancelled=True)
        entry = parse(self.client.get("/calendar.ics")).walk("VEVENT")[0]
        self.assertEqual(str(entry["STATUS"]), "CANCELLED")

    def test_window(self):
        for days in (-8, -2, 30, 120):
            self.show(f"day {days}", "Boston", days=days)
        self.assertEqual(
            summaries(self.client.get("/calendar.ics")),
            ["day -2 [New England Music]", "day 30 [New England Music]"],
        )

    def test_unapproved_event_left_out(self):
        self.show("waiting", "Boston", is_approved=False)
        self.show("approved", "Boston")
        self.assertEqual(summaries(self.client.get("/calendar.ics")), ["approved [New England Music]"])

    def test_calendar_name_and_refresh(self):
        response = self.client.get("/calendar.ics?metro=" + self.slug("MA: Cape Cod"))
        cal = parse(response)
        self.assertEqual(str(cal["X-WR-CALNAME"]), "New England Music: MA: Cape Cod")
        text = response.content.decode()
        self.assertIn("REFRESH-INTERVAL;VALUE=DURATION:PT6H", text)
        self.assertIn("X-PUBLISHED-TTL:PT6H", text)
        self.assertEqual(str(parse(self.client.get("/calendar.ics"))["X-WR-CALNAME"]), "New England Music")

    def test_calendar_name_from_the_settings(self):
        with self.settings(SITE_NAME="Boston Shows"):
            response = self.client.get("/calendar.ics?state=" + self.slug("Vermont"))
        self.assertEqual(str(parse(response)["X-WR-CALNAME"]), "Boston Shows: Vermont")
        self.assertIn("Boston Shows", str(parse(response)["X-WR-CALDESC"]))

    def test_unchanged_feed(self):
        self.show("boston show", "Boston")
        first = self.client.get("/calendar.ics")
        self.assertEqual(first["Cache-Control"], "public, max-age=3600")
        again = self.client.get("/calendar.ics", HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")

    def test_changed_feed(self):
        self.show("boston show", "Boston")
        first = self.client.get("/calendar.ics")
        self.show("new show", "Boston", days=4)
        again = self.client.get("/calendar.ics", HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 200)
        self.assertIn("new show [New England Music]", summaries(again))
        self.assertNotEqual(again["ETag"], first["ETag"])


class SubscribeLinksTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()

    def links(self, path):
        return self.client.get(path).context["calendar_links"]

    def test_subscribe_to_a_state(self):
        slug = GeoArea.objects.get(label="Vermont").slug
        month = timezone.localtime().strftime("/%Y-%m/")
        for path in (f"/?state={slug}", f"{month}?state={slug}"):
            response = self.client.get(path)
            links = response.context["calendar_links"]
            self.assertTrue(links["url"].endswith(f"/calendar.ics?state={slug}"), path)
            self.assertTrue(links["url"].startswith("http"), path)
            self.assertEqual(links["webcal"], "webcal://" + links["url"].split("://", 1)[1])
            self.assertTrue(links["google"].startswith("https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2F"))
            self.assertIn(f"calendar.ics%3Fstate%3D{slug}", links["google"])
            self.assertContains(response, "Subscribe to this calendar: Vermont")
            self.assertContains(response, f'href="{links["webcal"]}"')

    def test_nothing_chosen(self):
        response = self.client.get("/")
        links = response.context["calendar_links"]
        self.assertTrue(links["url"].endswith("/calendar.ics"))
        self.assertContains(response, "<summary>Subscribe to this calendar</summary>", html=False)
