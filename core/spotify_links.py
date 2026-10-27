"""
the spotify artists the listing's play buttons link to, from SpotifyArtistLink: used when an
event's html is baked, and by match_spotify_artists and the admin to re-bake the events whose
links changed.

an event's name gets a button when its own link is matched. failing that:
- a duo billing ("Connor Garvey & Ben Cosgrove") gets one per matched act (name_parts);
- an occasion ("Built to Spill Fall 2026 Tour") gets the artist it starts with
  (occasion_prefix), labelled with that part of the name.
"""

from django.utils import timezone

from core.artist_matching import normalize
from core.artist_names import event_artist_names, name_parts, occasion_prefix
from core.spotify import credentials


def upcoming_music_events():
    """upcoming approved events, with what baking needs; music is filtered per event"""
    from core.models import Event

    return Event.objects.filter(starttime__gte=timezone.now()).select_related("venue")


def word_prefixes(key):
    words = key.split()
    return {" ".join(words[:end]) for end in range(1, len(words))}


def candidate_keys(name):
    """every link that could give this name a button: its own, its acts', its prefixes'"""
    key = normalize(name)
    return {key} | {normalize(part) for part in name_parts(name)} | word_prefixes(key)


def buttons_for(name, ids):
    """[(label, spotify artist id)] for one name, given the matched links' ids by key"""
    key = normalize(name)
    if key in ids:
        return [(name, ids[key])]
    parts = [(part, ids[normalize(part)]) for part in name_parts(name) if normalize(part) in ids]
    if parts:
        return parts
    prefix = occasion_prefix(key, ids)
    if prefix:
        # label with the event's own spelling of the artist: its first words
        return [(" ".join(name.split()[: len(prefix.split())]), ids[prefix])]
    return []


def event_spotify_artists(event):
    """[(name as the event writes it, spotify artist id)] for the event's matched artists"""
    from core.models import SpotifyArtistLink

    if not credentials():
        return []
    names = event_artist_names(event)
    if not names:
        return []
    ids = dict(
        SpotifyArtistLink.objects.filter(
            name_key__in=set().union(*(candidate_keys(name) for name in names)),
            status=SpotifyArtistLink.Status.MATCHED,
        )
        .exclude(spotify_artist_id="")
        .values_list("name_key", "spotify_artist_id")
    )
    buttons, seen = [], set()
    for name in names:
        for label, artist_id in buttons_for(name, ids):
            if artist_id not in seen:
                seen.add(artist_id)
                buttons.append((label, artist_id))
    return buttons


def rebake_events_naming(name_keys, events=None):
    """re-bake the upcoming events that could show any of these artists; how many were"""
    from core.models import Event
    from core.utils_event_caching import bake_event_html

    name_keys = set(name_keys)
    if not name_keys:
        return 0
    rebaked = 0
    for event in upcoming_music_events() if events is None else events:
        if name_keys & set().union(set(), *(candidate_keys(name) for name in event_artist_names(event))):
            # update() rather than save(): nothing else about the event changed
            Event.all_objects.filter(pk=event.pk).update(baked_html_template=bake_event_html(event))
            rebaked += 1
    return rebaked
