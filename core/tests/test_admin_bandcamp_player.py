import io
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core import bandcamp_embeds
from core.artist_import import import_rows, rows_from_csv
from core.event_performers import link_from_names
from core.models import Artist, Band, Event, EventPerformer, MusicAct

KRILL = "https://krill.bandcamp.com/"
Embed = MusicAct.BandcampEmbedStatus


def form_data(act, **changes):
    """the admin's form as posted, as a browser sends it"""
    data = {
        "name": act.name, "slug": act.slug, "act_id": act.act_id or "", "city_town": act.city_town, "state": act.state,
        "website": act.website, "bandcamp_url": act.bandcamp_url, "notes": act.notes, "musicbrainz_id": act.musicbrainz_id or "",
        "bandcamp_embed_kind": act.bandcamp_embed_kind, "bandcamp_embed_id": act.bandcamp_embed_id,
        "memberships-TOTAL_FORMS": "0", "memberships-INITIAL_FORMS": "0",
        "memberships-MIN_NUM_FORMS": "0", "memberships-MAX_NUM_FORMS": "1000",
    }
    data.update(changes)
    return data


def found(model=Band, name="Krill", **fields):
    values = dict(
        name=name, bandcamp_url=KRILL, bandcamp_embed_kind="album", bandcamp_embed_id="5", bandcamp_embed_status="found",
        bandcamp_embed_for=KRILL, bandcamp_embed_checked_at=timezone.now(),
    )
    return model.objects.create(**{**values, **fields})


class BandcampPlayerAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        patcher = mock.patch("core.event_performers.rebake")
        self.rebake = patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, act, **changes):
        name = act._meta.model_name
        return self.client.post(reverse(f"admin:core_{name}_change", args=[act.pk]), form_data(act, **changes))

    def action(self, model, name, *acts):
        return self.client.post(
            reverse(f"admin:core_{model._meta.model_name}_changelist"), {"action": name, "_selected_action": [a.pk for a in acts]}
        )

    def performing(self, act, title="show"):
        event = Event.all_objects.create(title=title, starttime=timezone.now() + timedelta(days=3))
        EventPerformer.objects.create(event=event, **{"band" if isinstance(act, Band) else "artist": act})
        return event

    def test_the_change_page_has_the_fieldset(self):
        band = found()
        html = self.client.get(reverse("admin:core_band_change", args=[band.pk])).content.decode()
        self.assertIn("Bandcamp player", html)
        self.assertIn("bandcamp_embed_id", html)

    def test_an_editor_sets_an_id(self):
        for model in (Band, Artist):
            with self.subTest(model=model):
                act = model.objects.create(name=f"Act {model.__name__}", bandcamp_url=KRILL)
                response = self.post(act, bandcamp_embed_kind="album", bandcamp_embed_id="777")
                self.assertEqual(response.status_code, 302)
                act.refresh_from_db()
                self.assertEqual((act.bandcamp_embed_kind, act.bandcamp_embed_id), ("album", "777"))
                self.assertEqual(act.field_sources["bandcamp_embed"], "editor")
                self.assertNotIn("bandcamp_embed_kind", act.field_sources)
                # the status stays blank, and the player is usable at once
                self.assertEqual(act.bandcamp_embed_status, "")
                self.assertTrue(act.bandcamp_player_usable)

    def test_an_editors_player_is_shown_whatever_the_url(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.post(band, bandcamp_embed_kind="track", bandcamp_embed_id="9")
        self.post(Band.objects.get(), bandcamp_url="https://krill-new.bandcamp.com/", bandcamp_embed_kind="track", bandcamp_embed_id="9")
        self.assertTrue(Band.objects.get().bandcamp_player_usable)

    def test_an_id_that_is_not_a_number(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        response = self.post(band, bandcamp_embed_kind="album", bandcamp_embed_id='12ab"><script>')
        self.assertEqual(response.status_code, 200)
        self.assertIn("a number", response.content.decode())
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id, band.field_sources), ("", "", {}))

    def test_the_kind_and_the_id_go_together(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        for changes in ({"bandcamp_embed_kind": "album"}, {"bandcamp_embed_id": "5"}):
            response = self.post(band, **changes)
            self.assertEqual(response.status_code, 200)
            self.assertIn("together", response.content.decode())

    def test_saving_without_touching_the_player_keeps_a_found_one_unmarked(self):
        band = found()
        self.post(band, notes="x")
        band.refresh_from_db()
        self.assertEqual(band.field_sources, {"notes": "editor"})
        self.assertEqual((band.bandcamp_embed_status, band.bandcamp_embed_id), ("found", "5"))

    def test_events_re_rendered_after_an_editors_change(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        event = self.performing(band)
        for changes in (
            {"bandcamp_embed_kind": "album", "bandcamp_embed_id": "777"},
            {"bandcamp_url": "https://krill-new.bandcamp.com/"},
            {"notes": "any save"},
        ):
            self.rebake.reset_mock()
            self.post(Band.objects.get(), **changes)
            self.rebake.assert_called_once_with(event)

    def test_events_re_rendered_after_clearing_and_declining(self):
        band = found()
        event = self.performing(band)
        self.action(Band, "decline_bandcamp_player", band)
        self.rebake.assert_called_once_with(event)

    def test_events_re_rendered_after_marking_ready(self):
        band = Band.objects.create(name="Krill", needs_review=True, review_reasons=["not_found"])
        event = self.performing(band)
        self.action(Band, "mark_ready", band)
        self.rebake.assert_called_with(event)

    def test_events_re_rendered_after_performer_links_change(self):
        band = found()
        event = Event.all_objects.create(title="Krill", artists="Krill", starttime=timezone.now() + timedelta(days=3))
        link_from_names(event)
        self.rebake.assert_called_once_with(event)

    def test_deleting_an_act_re_renders_its_events_once(self):
        band = found()
        event = self.performing(band)
        response = self.client.post(reverse("admin:core_band_delete", args=[band.pk]), {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Band.objects.exists())
        self.rebake.assert_called_once_with(event)

    def test_clearing(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        self.post(band, bandcamp_embed_kind="album", bandcamp_embed_id="777")
        self.post(Band.objects.get(), bandcamp_embed_kind="", bandcamp_embed_id="")
        band = Band.objects.get()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id), ("", ""))
        self.assertNotIn("bandcamp_embed", band.field_sources)
        # the next run looks it up
        self.assertTrue(bandcamp_embeds.due(band, timezone.now()))

    def test_clearing_a_found_player_makes_the_band_due_again(self):
        band = found()
        self.post(band, bandcamp_embed_kind="", bandcamp_embed_id="")
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_status, band.bandcamp_embed_for), ("", "", ""))
        self.assertTrue(bandcamp_embeds.due(band, timezone.now()))

    def test_filter(self):
        found(name="Krill")
        Band.objects.create(name="Pile", bandcamp_url="https://pile.bandcamp.com/", bandcamp_embed_status="no_playable")
        url = reverse("admin:core_band_changelist")
        response = self.client.get(url + "?bandcamp_embed_status__exact=no_playable")
        self.assertEqual({b.name for b in response.context["cl"].result_list}, {"Pile"})
        self.assertContains(self.client.get(url), "No playable release")

    def test_clearing_a_match_keeps_the_player(self):
        band = found(field_sources={"bandcamp_url": "musicbrainz"}, musicbrainz_id="11111111-1111-4111-8111-111111111111")
        self.action(Band, "clear_musicbrainz_match", band)
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_kind, band.bandcamp_embed_id, band.bandcamp_embed_status), ("album", "5", "found"))
        # the musicbrainz link went, so the found player is stale until the lookup runs
        self.assertEqual(band.bandcamp_url, "")
        self.assertFalse(band.bandcamp_player_usable)

    def test_clearing_a_match_keeps_an_editors_player(self):
        band = found(field_sources={"bandcamp_embed": "editor"})
        self.action(Band, "clear_musicbrainz_match", band)
        band.refresh_from_db()
        self.assertEqual(band.field_sources, {"bandcamp_embed": "editor"})

    def test_clearing_a_match_re_renders_events(self):
        band = found(field_sources={"bandcamp_url": "musicbrainz"})
        event = self.performing(band)
        self.action(Band, "clear_musicbrainz_match", band)
        self.rebake.assert_called_once_with(event)

    def test_the_import_leaves_the_player_and_asks_bandcamp_for_nothing(self):
        for model, kind in ((Band, "band"), (Artist, "artist")):
            with self.subTest(kind=kind):
                act = found(model, name=f"Import {kind}", act_id=f"A-{kind}")
                header = "Act_ID,Name,Kind,Town,Website,Bandcamp\n"
                row = f"A-{kind},Import {kind},{kind},Boston,https://x.example,{KRILL}\n"
                with mock.patch("requests.Session.request", side_effect=AssertionError("no requests")) as request:
                    import_rows(rows_from_csv(io.StringIO(header + row)))
                request.assert_not_called()
                act.refresh_from_db()
                self.assertEqual((act.bandcamp_embed_kind, act.bandcamp_embed_id, act.bandcamp_embed_status), ("album", "5", "found"))
                self.assertEqual(act.city_town, "Boston")

    def test_events_re_rendered_after_the_import_changes_the_address(self):
        for model, kind in ((Band, "band"), (Artist, "artist")):
            with self.subTest(kind=kind):
                self.rebake.reset_mock()
                act = found(model, name=f"Import {kind}", act_id=f"A-{kind}", field_sources={"bandcamp_url": "import"})
                event = self.performing(act)
                header = "Act_ID,Name,Kind,Bandcamp\n"
                import_rows(rows_from_csv(io.StringIO(header + f"A-{kind},Import {kind},{kind},https://new-{kind}.bandcamp.com/\n")))
                self.rebake.assert_called_once_with(event)
                self.assertFalse(model.objects.get(pk=act.pk).bandcamp_player_usable)

    def test_import_alone_does_not_re_render_without_a_change(self):
        found(act_id="A1", field_sources={"bandcamp_url": "import"})
        import_rows(rows_from_csv(io.StringIO(f"Act_ID,Name,Kind,Bandcamp\nA1,Krill,band,{KRILL}\n")))
        self.rebake.assert_not_called()

    # declined acts

    def test_declined_act(self):
        band = found()
        self.action(Band, "decline_bandcamp_player", band)
        band.refresh_from_db()
        self.assertEqual((band.bandcamp_embed_status, band.bandcamp_embed_kind, band.bandcamp_embed_id), ("declined", "", ""))
        self.assertFalse(band.bandcamp_player_usable)
        self.assertFalse(bandcamp_embeds.due(band, timezone.now(), refresh=True))
        # no listening section on its page
        self.assertNotIn("Listen on Bandcamp", self.client.get(band.get_absolute_url()).content.decode())

    def test_declining_removes_a_found_player_and_an_editors(self):
        mine = found(name="Mine", field_sources={"bandcamp_embed": "editor", "website": "editor"})
        self.action(Band, "decline_bandcamp_player", mine)
        mine.refresh_from_db()
        self.assertEqual(mine.field_sources, {"website": "editor"})
        self.assertEqual((mine.bandcamp_embed_kind, mine.bandcamp_embed_status), ("", "declined"))

    def test_clearing_does_not_lift_a_decline(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL, bandcamp_embed_status="declined")
        self.post(band, notes="x")
        self.assertEqual(Band.objects.get().bandcamp_embed_status, "declined")
        found_declined = Band.objects.create(name="Odd", bandcamp_url=KRILL, bandcamp_embed_status="declined", bandcamp_embed_kind="album", bandcamp_embed_id="3")
        self.post(found_declined, bandcamp_embed_kind="", bandcamp_embed_id="")
        found_declined.refresh_from_db()
        self.assertEqual(found_declined.bandcamp_embed_status, "declined")
        self.assertFalse(bandcamp_embeds.due(found_declined, timezone.now()))

    def test_a_declined_act_cannot_be_given_a_player_by_hand(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL, bandcamp_embed_status="declined")
        response = self.post(band, bandcamp_embed_kind="album", bandcamp_embed_id="777")
        self.assertEqual(response.status_code, 200)
        self.assertIn("declined", response.content.decode())

    def test_an_editor_lifts_a_decline(self):
        band = Band.objects.create(
            name="Krill", bandcamp_url=KRILL, bandcamp_embed_status="declined", bandcamp_embed_for=KRILL,
            bandcamp_embed_checked_at=timezone.now(),
        )
        self.action(Band, "lift_bandcamp_decline", band)
        band.refresh_from_db()
        self.assertEqual(band.bandcamp_embed_status, "")
        self.assertTrue(bandcamp_embeds.due(band, timezone.now()))
