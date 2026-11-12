"""
what the discovery deck's tests share: acts with shows, and the three services' links for
an act's name. no service is called: a link is a row, as in the preview tests.
"""

import datetime

from core.models import (
    AppleMusicArtistLink, Artist, Band, Event, EventPerformer, SpotifyArtistLink, Venue, YouTubeArtistLink,
)
from django.utils import timezone


def days(n):
    return timezone.now() + datetime.timedelta(days=n)


def show(act, when, venue=None, approved=True, cancelled=False, **fields):
    event = Event.all_objects.create(
        title="show", starttime=when, venue=venue, is_approved=approved, is_cancelled=cancelled, **fields
    )
    EventPerformer.objects.create(event=event, **({"band": act} if isinstance(act, Band) else {"artist": act}))
    return event


def venue(name="Lupo's", town="Providence", state="RI", sheet_id="V1"):
    return Venue.objects.create(sheet_id=sheet_id, name=name, city_town=town, state=state)


def spotify(name_key, artist_id="sp123"):
    now = timezone.now()
    return SpotifyArtistLink.objects.create(
        name_key=name_key, status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id=artist_id,
        checked_at=now, last_seen_at=now,
    )


def apple(name_key, artist_id="100", song_id="200", album_id="300"):
    now = timezone.now()
    return AppleMusicArtistLink.objects.create(
        name_key=name_key, status=AppleMusicArtistLink.Status.MATCHED, apple_artist_id=artist_id,
        top_song_id=song_id, top_album_id=album_id, checked_at=now, last_seen_at=now,
    )


def youtube(name_key, video_id="vid123", channel_id="UCchannel"):
    now = timezone.now()
    return YouTubeArtistLink.objects.create(
        name_key=name_key, status=YouTubeArtistLink.Status.MATCHED, video_id=video_id, channel_id=channel_id,
        checked_at=now, last_seen_at=now,
    )
