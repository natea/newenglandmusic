from datetime import timedelta

from core.geo_filters import COOKIE_NAME as GEO_COOKIE
from core.models import Event, Venue
from core.saved_shows import COOKIE_NAME, MAX_SAVED, format_saved, parse_saved
from core.tests.geo_fixture import load_geo_fixture
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from django.test import SimpleTestCase, TestCase


class ParseSavedTestCase(SimpleTestCase):
    def test_malformed_cookie(self):
        self.assertEqual(parse_saved("12,abc,,-3,12"), [12])
        self.assertEqual(parse_saved(" 7 , 0, 3.5, 9"), [7, 9])
        self.assertEqual(parse_saved(None), [])

    def test_commas_encoded_as_the_browser_writes_them(self):
        self.assertEqual(parse_saved("30%2C10%2C20"), [30, 10, 20])

    def test_order_kept(self):
        self.assertEqual(parse_saved("30,10,20"), [30, 10, 20])
        self.assertEqual(format_saved([30, 10, 20]), "30%2C10%2C20")
        self.assertEqual(parse_saved(format_saved([30, 10, 20])), [30, 10, 20])

    def test_limit(self):
        ids = parse_saved(",".join(str(n) for n in range(1, MAX_SAVED + 50)))
        self.assertEqual(len(ids), MAX_SAVED)
        self.assertEqual(ids[0], 1)


class SavedPageTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        self.today = beginning_of_day(get_current_new_york_datetime())
        self.boston = Venue.objects.create(name="Boston venue", state="MA", county="Suffolk", city_town="Boston")
        self.vermont = Venue.objects.create(name="Burlington venue", state="VT", county="Chittenden", city_town="Burlington")

    def event(self, title, days, hour=20, venue=None, **fields):
        return Event.objects.create(
            title=title, starttime=self.today + timedelta(days=days, hours=hour), venue=venue or self.boston, **fields
        )

    def get(self, ids, path="/saved", **cookies):
        self.client.cookies[COOKIE_NAME] = format_saved(ids)
        for name, value in cookies.items():
            self.client.cookies[name] = value
        return self.client.get(path)

    def titles(self, response):
        return [event.title for day in response.context["grouped_events_as_list"] for event in day["events"]]

    def test_grouped_by_date(self):
        late = self.event("late nov 6", 6, hour=22)
        early = self.event("early nov 6", 6, hour=19)
        later = self.event("nov 8", 8)
        self.event("not saved", 6)
        response = self.get([later.pk, late.pk, early.pk])
        groups = response.context["grouped_events_as_list"]
        self.assertEqual([len(day["events"]) for day in groups], [2, 1])
        self.assertEqual(groups[0]["date"], (self.today + timedelta(days=6)).date())
        self.assertEqual(self.titles(response), ["early nov 6", "late nov 6", "nov 8"])
        # each event as the listing shows it, with its icon row
        self.assertContains(response, f'id="event-{early.pk}"')
        self.assertContains(response, 'class="event-actions"', count=3)

    def test_area_filter_ignored(self):
        boston_show = self.event("boston show", 2)
        response = self.get([boston_show.pk], **{GEO_COOKIE: "state=vermont"})
        self.assertEqual(self.titles(response), ["boston show"])
        self.assertNotIn(GEO_COOKIE, response.cookies)

    def test_area_filter_ignored_even_in_the_url(self):
        boston_show = self.event("boston show", 2)
        self.client.cookies[COOKIE_NAME] = format_saved([boston_show.pk])
        response = self.client.get("/saved?state=vermont")
        self.assertEqual(self.titles(response), ["boston show"])
        self.assertNotIn(GEO_COOKIE, response.cookies)

    def test_nothing_saved(self):
        response = self.client.get("/saved")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No saved shows yet")
        self.assertContains(response, "bookmark icon")

    def test_none_upcoming(self):
        past = self.event("last week", -7)
        response = self.get([past.pk])
        self.assertContains(response, "No saved shows yet")

    def test_unknown_group(self):
        show = self.event("a show", 3)
        response = self.get([show.pk], path="/saved?group=venue")
        self.assertEqual(response.context["group"], "date")
        self.assertEqual(self.titles(response), ["a show"])

    def test_past_show_dropped(self):
        past = self.event("yesterday", -1)
        upcoming = self.event("tomorrow", 1)
        response = self.get([past.pk, upcoming.pk])
        self.assertEqual(self.titles(response), ["tomorrow"])
        self.assertEqual(response.cookies[COOKIE_NAME].value, str(upcoming.pk))

    def test_earlier_today_still_listed(self):
        tonight = self.event("earlier today", 0, hour=0)
        response = self.get([tonight.pk])
        self.assertEqual(self.titles(response), ["earlier today"])

    def test_deleted_or_unapproved_show_dropped(self):
        deleted = self.event("deleted", 2)
        deleted_pk = deleted.pk
        deleted.delete()
        unapproved = self.event("unapproved", 2, is_approved=False)
        kept = self.event("kept", 3)
        response = self.get([deleted_pk, unapproved.pk, kept.pk])
        self.assertEqual(self.titles(response), ["kept"])
        self.assertEqual(response.cookies[COOKIE_NAME].value, str(kept.pk))

    def test_cookie_order_kept_newest_first(self):
        first, second = self.event("first", 5), self.event("second", 2)
        response = self.get([first.pk, second.pk])
        # listed by date, but the cookie keeps the visitor's order
        self.assertEqual(self.titles(response), ["second", "first"])
        self.assertEqual(parse_saved(response.cookies[COOKIE_NAME].value), [first.pk, second.pk])
        # written as the browser writes it, unquoted
        self.assertEqual(response.cookies[COOKIE_NAME].value, f"{first.pk}%2C{second.pk}")
        self.assertEqual(response.cookies[COOKIE_NAME]["samesite"], "Lax")

    def test_malformed_cookie_rewritten(self):
        show = self.event("a show", 2)
        self.client.cookies[COOKIE_NAME] = f"{show.pk},abc,,-3,{show.pk}"
        response = self.client.get("/saved")
        self.assertEqual(response.cookies[COOKIE_NAME].value, str(show.pk))

    def test_cookie_cleared_when_nothing_is_left(self):
        past = self.event("last week", -7)
        response = self.get([past.pk])
        self.assertEqual(response.cookies[COOKIE_NAME].value, "")
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)


class SaveLinkRenderTestCase(TestCase):
    def setUp(self):
        self.show = Event.objects.create(
            title="a show", starttime=beginning_of_day(get_current_new_york_datetime()) + timedelta(days=1, hours=20)
        )

    def test_bookmark_is_a_form_on_the_page_not_in_the_stored_html(self):
        stored = Event.objects.get(pk=self.show.pk).baked_html_template
        self.assertIn("<!--event-actions-->", stored)
        self.assertNotIn('class="save', stored)
        html = self.client.get("/").content.decode()
        self.assertIn(
            f'<form class="save-form" method="post" action="/saved/toggle/{self.show.pk}">', html
        )

    def test_header_link_on_every_page(self):
        for path in ("/", "/saved"):
            response = self.client.get(path)
            self.assertContains(response, '<a href="/saved" class="saved-count">Saved shows</a>', msg_prefix=path)
            self.assertContains(response, "core/js/saved_shows.js", msg_prefix=path)
