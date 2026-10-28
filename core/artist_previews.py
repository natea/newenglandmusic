"""
the play buttons an event's html is baked with: one entry per artist, each with its spotify
artist id and its apple music artist, top song and album, whichever are matched.

spotify buttons come from SpotifyArtistLink, including its fallbacks (a duo's acts, the
artist an occasion starts with: see core/spotify_links.py). apple music buttons come from
AppleMusicArtistLink, for the event's names as written, and only when APPLE_MUSIC_PREVIEWS
is on; youtube buttons likewise from YouTubeArtistLink, when YOUTUBE_PREVIEWS is on. an
artist matched on several gets their buttons side by side.
"""

from core.apple_music import previews_enabled
from core import youtube
from core.artist_matching import normalize
from core.artist_names import event_artist_names
from core.spotify import credentials as spotify_credentials
from core.spotify_links import event_spotify_artists
from core.youtube_links import event_youtube_artists


def event_apple_music_artists(event, names):
    """{normalized name: {"artist", "song", "album"}} for the names matched with a top song"""
    from core.models import AppleMusicArtistLink

    if not names or not previews_enabled():
        return {}
    rows = (
        AppleMusicArtistLink.objects.filter(
            name_key__in={normalize(name) for name in names}, status=AppleMusicArtistLink.Status.MATCHED
        )
        .exclude(top_song_id="")
        .exclude(top_album_id="")
        .values_list("name_key", "apple_artist_id", "top_song_id", "top_album_id")
    )
    return {key: {"artist": artist, "song": song, "album": album} for key, artist, song, album in rows}


def event_artist_previews(event):
    """
    [{"label", "spotify" (an id or None), "apple" (ids or None), "youtube" (ids or None)}],
    in the event's order
    """
    if not spotify_credentials() and not previews_enabled() and not youtube.previews_enabled():
        return []
    names = event_artist_names(event)
    apple = event_apple_music_artists(event, names)
    on_youtube = event_youtube_artists(names)
    entries = {}

    def entry(key, label):
        return entries.setdefault(key, {"label": label, "spotify": None, "apple": None, "youtube": None})

    for label, spotify_id in event_spotify_artists(event):
        entry(normalize(label), label)["spotify"] = spotify_id
    for name in names:
        key = normalize(name)
        if key in apple:
            entry(key, name)["apple"] = apple[key]
        if key in on_youtube:
            entry(key, name)["youtube"] = on_youtube[key]
    # the event's own order: spotify's labels can be part of a name ("Built to Spill" from
    # "Built to Spill Fall 2026 Tour", "Boulder Canyon" from a duo), so each label goes where
    # the first name containing it is
    order = {normalize(name): index for index, name in enumerate(names)}

    def position(key):
        if key in order:
            return order[key]
        within = (index for name_key, index in order.items() if f" {key} " in f" {name_key} ")
        return min(within, default=len(order))

    return [entries[key] for key in sorted(entries, key=position)]
