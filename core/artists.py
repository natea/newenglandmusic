"""
artist and band records (Artist, Band, BandMembership): what's shared by their import
(import_artists), their musicbrainz enrichment (enrich_artists_from_musicbrainz) and the
admin.

bandcamp has no public api and its acceptable use policy forbids scraping, so nothing is
ever requested from it: a record keeps only a link to its bandcamp page, typed by an
editor, given in the import, or listed by musicbrainz.
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
