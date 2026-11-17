"""
artist and band records (Artist, Band, BandMembership): what's shared by their import
(import_artists), their musicbrainz enrichment (enrich_artists_from_musicbrainz) and the
admin.

bandcamp has no public api and its acceptable use policy forbids scraping, so the only
thing ever requested from it is, by find_bandcamp_embeds, an act's own page and player, to
read the numeric id of a release the embedded player can play. nothing else is scraped, no
proxy is used, and enrichment, the imports and the link-hub reader request nothing from it.
a record's bandcamp link is typed by an editor, given in the import, listed by musicbrainz
or read from its link hub.
"""

from urllib.parse import urlsplit

from django.core.exceptions import ValidationError


MBID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def is_bandcamp_url(url):
    """an https url on bandcamp.com or one of its subdomains ("krill.bandcamp.com")"""
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and (host == "bandcamp.com" or host.endswith(".bandcamp.com"))


def validate_bandcamp_url(url):
    if url and not is_bandcamp_url(url):
        raise ValidationError("a bandcamp page: https://… on bandcamp.com")


def is_embed_id(value):
    return bool(value) and value.isascii() and value.isdigit()


def validate_bandcamp_embed_id(value):
    if value and not is_embed_id(value):
        raise ValidationError("a number: the digits of a Bandcamp album or track id")


def bandcamp_player_url(kind, embed_id):
    """
    bandcamp's large player for an album or track, or "" unless the kind is known and the id
    is all digits: only those two reach the address
    """
    if kind not in ("album", "track") or not is_embed_id(embed_id or ""):
        return ""
    return f"https://bandcamp.com/EmbeddedPlayer/{kind}={embed_id}/size=large/tracklist=true/artwork=small/"
