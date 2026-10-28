import datetime
from unittest import mock

from core.models import Event, YouTubeArtistLink
from core.tests.youtube_fixture import DINOSAUR_CHANNEL, SWITCHED_ON, FakeWeb, video
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

Status, Evidence, Source = YouTubeArtistLink.Status, YouTubeArtistLink.Evidence, YouTubeArtistLink.Source
RICK = "dQw4w9WgXcQ"
RICK_CHANNEL = "UCuAXFkgsw1L7xaCfnd5JJOw"


class YouTubeLinkAdminTestCase(TestCase):
    def setUp(self):
        # no spotify or apple music: an editor's youtube match shows a button on its own
        self.enterContext(mock.patch.dict("os.environ", SWITCHED_ON))
        self.web = FakeWeb(videos={RICK: video(RICK, RICK_CHANNEL, "Rick Astley", "Never Gonna Give You Up")})
        self.enterContext(mock.patch("core.youtube.client", lambda: self.web.youtube()))
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.event = Event.objects.create(artists="Rick Astley", starttime=timezone.now() + datetime.timedelta(days=2))

    def baked(self):
        return Event.objects.get(pk=self.event.pk).baked_html_template

    def add(self, link):
        return self.client.post(reverse("admin:core_youtubeartistlink_add"), {"name_key": "Rick Astley", "youtube_link": link})

    def test_editor_pastes_a_short_video_link(self):
        self.assertNotIn("youtube-play", self.baked())
        self.assertEqual(self.add(f"https://youtu.be/{RICK}").status_code, 302)
        link = YouTubeArtistLink.objects.get(name_key="rick astley")
        self.assertEqual(
            (link.status, link.evidence, link.source, link.video_id, link.channel_id),
            (Status.MATCHED, Evidence.EDITOR, Source.EDITOR, RICK, RICK_CHANNEL),
        )
        self.assertIn(f'data-youtube-video="{RICK}"', self.baked())

    def test_editor_pastes_a_watch_link(self):
        self.add(f"https://www.youtube.com/watch?v={RICK}")
        self.assertEqual(YouTubeArtistLink.objects.get().video_id, RICK)

    def test_editor_pastes_a_channel(self):
        self.add(f"https://www.youtube.com/channel/{DINOSAUR_CHANNEL}")
        link = YouTubeArtistLink.objects.get()
        self.assertEqual((link.status, link.channel_id, link.video_id), (Status.MATCHED, DINOSAUR_CHANNEL, ""))
        self.assertIn(f'href="https://www.youtube.com/channel/{DINOSAUR_CHANNEL}"', self.baked())

    def test_unembeddable_video_shows_no_button(self):
        self.web.videos[RICK]["status"]["embeddable"] = False
        self.add(f"https://youtu.be/{RICK}")
        self.assertEqual(YouTubeArtistLink.objects.get().status, Status.NOT_FOUND)
        self.assertNotIn("youtube-play", self.baked())

    def test_invalid_link_rejected(self):
        now = timezone.now()
        link = YouTubeArtistLink.objects.create(
            name_key="rick astley", status=Status.MATCHED, evidence=Evidence.TOPIC_SONG, video_id=RICK,
            channel_id=RICK_CHANNEL, checked_at=now, last_seen_at=now,
        )
        response = self.client.post(
            reverse("admin:core_youtubeartistlink_change", args=[link.pk]),
            {"name_key": "Rick Astley", "youtube_link": "https://open.spotify.com/artist/abc123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "isn&#x27;t a YouTube channel or video link")
        link.refresh_from_db()
        self.assertEqual((link.video_id, link.source), (RICK, Source.AUTO))

    def test_editor_marks_no_youtube(self):
        now = timezone.now()
        link = YouTubeArtistLink.objects.create(
            name_key="rick astley", status=Status.MATCHED, evidence=Evidence.TOPIC_SONG, video_id=RICK,
            channel_id=RICK_CHANNEL, checked_at=now, last_seen_at=now,
        )
        self.event.save()
        self.assertIn("youtube-play", self.baked())
        self.client.post(
            reverse("admin:core_youtubeartistlink_changelist"),
            {"action": "mark_no_youtube", "_selected_action": [link.pk]},
        )
        link.refresh_from_db()
        self.assertEqual((link.status, link.source, link.video_id), (Status.NONE, Source.EDITOR, ""))
        self.assertNotIn("youtube-play", self.baked())

    def test_filters(self):
        response = self.client.get(reverse("admin:core_youtubeartistlink_changelist") + "?evidence=wikidata&status=matched&source=auto")
        self.assertEqual(response.status_code, 200)
