"""
the play buttons an event's html is baked with: one entry per artist, each with its spotify
artist id and its apple music artist, top song and album, whichever are matched.

spotify buttons come from SpotifyArtistLink, including its fallbacks (a duo's acts, the
artist an occasion starts with: see core/spotify_links.py). apple music buttons come from
AppleMusicArtistLink, for the event's names as written, and only when APPLE_MUSIC_PREVIEWS
is on; youtube buttons likewise from YouTubeArtistLink, when YOUTUBE_PREVIEWS is on. an
artist matched on several gets their buttons side by side.

bandcamp buttons come from the performers an event is linked to (EventPerformer) that have a
usable Bandcamp player (MusicAct.bandcamp_player_usable), whether or not any other service is
switched on. the buttons' order on each screen is in ORDERS, through players_in_order.

act_previews is the same for acts' own names, for the discovery deck's cards.
"""

from core.apple_music import previews_enabled
from core.artist_matching import normalize
from core.artist_names import event_artist_names
from core.spotify import credentials as spotify_credentials
from core.spotify_links import buttons_for, event_spotify_artists
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


# each screen's order of players: the event row keeps its own, and the discovery deck's puts
# bandcamp last in the order the deck's issue gives. nothing draws the deck yet
ORDERS = {
    "event": ("spotify", "apple", "youtube", "bandcamp"),
    "deck": ("youtube", "apple", "spotify", "bandcamp"),
}


def players_in_order(entry, screen):
    """[(service, its data)] for the players an entry (see event_artist_previews) has, in the screen's order"""
    return [(service, entry[service]) for service in ORDERS[screen] if entry.get(service)]


def event_bandcamp_players(event):
    """
    {normalized name: {"name", "kind", "id", "page"}} for the event's linked artists and bands
    with a usable Bandcamp player. "page" is the act's own Bandcamp address, or the player's
    own when an editor set a player without one
    """
    if not event.pk:
        return {}
    players = {}
    for performer in event.performers.select_related("artist", "band").order_by("order", "pk"):
        act = performer.act
        if act.needs_review or not act.bandcamp_player_usable:
            continue
        players.setdefault(
            act.name_key,
            {
                "name": act.name, "kind": act.bandcamp_embed_kind, "id": act.bandcamp_embed_id,
                "page": act.bandcamp_url, "link": act.bandcamp_url or act.bandcamp_player_url,
            },
        )
    return players


def event_artist_previews(event):
    """
    [{"label", "spotify" (an id or None), "apple" (ids or None), "youtube" (ids or None),
    "bandcamp" (kind, id and page or None)}], in the event's order
    """
    names = event_artist_names(event)
    apple = event_apple_music_artists(event, names)
    on_youtube = event_youtube_artists(names)
    on_bandcamp = event_bandcamp_players(event)
    entries = {}

    def entry(key, label):
        return entries.setdefault(
            key, {"label": label, "spotify": None, "apple": None, "youtube": None, "bandcamp": None}
        )

    for label, spotify_id in event_spotify_artists(event):
        entry(normalize(label), label)["spotify"] = spotify_id
    for name in names:
        key = normalize(name)
        if key in apple:
            entry(key, name)["apple"] = apple[key]
        if key in on_youtube:
            entry(key, name)["youtube"] = on_youtube[key]
    for key, player in on_bandcamp.items():
        entry(key, player["name"])["bandcamp"] = player
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


def act_spotify_artists(names):
    """{normalized name: spotify artist id} for the names matched on spotify"""
    from core.models import SpotifyArtistLink

    if not names or not spotify_credentials():
        return {}
    ids = dict(
        SpotifyArtistLink.objects.filter(
            name_key__in={normalize(name) for name in names}, status=SpotifyArtistLink.Status.MATCHED
        )
        .exclude(spotify_artist_id="")
        .values_list("name_key", "spotify_artist_id")
    )
    # only the act's own name is a key, so buttons_for finds no duo or occasion fallback
    return {normalize(name): buttons_for(name, ids)[0][1] for name in names if normalize(name) in ids}


def act_previews(names):
    """
    {normalized name: {"label", "youtube", "apple", "spotify"}} for the act names matched on
    any service, in one query per service however many names. a name matches only as written
    (no duo or occasion fallbacks), through the same links and switches as the listings, so
    a card never has a button a listing wouldn't. an apple match without a top song has none
    """
    names = list(names)
    spotify = act_spotify_artists(names)
    apple = event_apple_music_artists(None, names)
    on_youtube = event_youtube_artists(names)
    previews = {}
    for name in names:
        key = normalize(name)
        if key in previews or not (key in spotify or key in apple or key in on_youtube):
            continue
        previews[key] = {
            "label": name, "youtube": on_youtube.get(key), "apple": apple.get(key), "spotify": spotify.get(key),
        }
    return previews
