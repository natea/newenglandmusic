"""
which youtube channel or video is an artist's own, from YouTubeArtistLink: found by
match_youtube_artists, and read when an event's html is baked for its youtube buttons.

a name is matched only when evidence ties youtube to the artist it's already matched to on
spotify or apple music, never on its name alone, since most band names are shared. the
evidence, strongest first:
1. wikidata or musicbrainz links the artist's spotify or apple music id to a youtube channel;
2. the artist's apple music top song is on youtube from the artist's own channel, or from
   youtube's "<artist> - Topic" channel, whose videos youtube makes from the artist's
   distributor and describe as "<song> · <artist>" on "<album>". another act with the same
   name would also need a song, and an album, of the same name.
"""

from core.artist_matching import normalize
from core.youtube import previews_enabled

TOPIC_SUFFIX = " topic"


def channel_kind(channel_title, key):
    """"topic" for the artist's topic channel, "channel" for one with its name, else None"""
    title = normalize(channel_title)
    if title == f"{key}{TOPIC_SUFFIX}":
        return "topic"
    if title == key:
        return "channel"
    return None


def contains(text, part):
    """whether normalized `part` is a run of whole words in normalized `text`"""
    return bool(part) and f" {part} " in f" {text} "


def describes_song(description, key, song, album):
    """whether a topic video's description has "<song> · <artist>" and the album's line"""
    song, album = normalize(song), normalize(album)
    lines = [line.strip() for line in (description or "").splitlines() if line.strip()]
    credits = False
    for line in lines:
        parts = [normalize(part) for part in line.split("·")]
        if len(parts) > 1 and parts[0] == song and key in parts[1:]:
            credits = True
    return credits and bool(album) and any(normalize(line) == album for line in lines)


def confirming_video(ordered_ids, videos, key, song, album):
    """
    (evidence, video id, channel id) for the first result that's the artist's own recording
    of the song, a topic channel's first, or None
    """
    found = {}
    for video_id in ordered_ids:
        video = videos.get(video_id)
        if not video or not video["embeddable"]:
            continue
        kind = channel_kind(video["channel_title"], key)
        if kind == "topic" and describes_song(video["description"], key, song, album):
            found.setdefault("topic-song", (video_id, video["channel_id"]))
        elif kind == "channel" and contains(normalize(video["title"]), normalize(song)):
            found.setdefault("channel-song", (video_id, video["channel_id"]))
    for evidence in ("topic-song", "channel-song"):
        if evidence in found:
            return (evidence, *found[evidence])
    return None


def event_youtube_artists(names):
    """{normalized name: {"video", "channel"}} for the names matched on youtube"""
    from core.models import YouTubeArtistLink

    if not names or not previews_enabled():
        return {}
    rows = YouTubeArtistLink.objects.filter(
        name_key__in={normalize(name) for name in names}, status=YouTubeArtistLink.Status.MATCHED
    ).values_list("name_key", "video_id", "channel_id")
    return {key: {"video": video, "channel": channel} for key, video, channel in rows if video or channel}
