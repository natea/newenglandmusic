"""
the artist and band lists as csv rows, for the admin's "Export to CSV" buttons
(MusicActAdmin.export_csv_view).

the columns are listed by hand, never "every field", so a new act field isn't handed out by
accident: test_act_export fails until a new field is exported or named in NOT_EXPORTED.
what needs credit beside it (wikipedia's introduction, musicbrainz's genre tags) is never
exported, because a spreadsheet column can't carry the credit.
"""
from .models import Band, MusicAct
from .venue_export import cell

# MusicAct fields, in column order; "slug" becomes the public page's address (PAGE_HEADER)
ACT_COLUMNS = [
    "act_id", "name", "city_town", "state",
    "website", "bandcamp_url", "instagram_url", "youtube_url", "discogs_url", "link_hub_url", "link_hub_status",
    "notes", "slug", "needs_review", "review_reasons",
    "musicbrainz_id", "musicbrainz_status", "mb_type", "country", "area", "begin_date", "end_date",
    "disambiguation", "wikidata_id", "sources",
    "photo_file", "photo_author", "photo_license", "photo_license_url",
]
PAGE_HEADER = "page"

# fields left out on purpose, each needing a reason: add new fields to the columns or here
NOT_EXPORTED = {
    # bookkeeping, not a detail of the act
    "id",
    "name_key",
    "field_sources",
    "created_at",
    "updated_at",
    "musicbrainz_checked_at",
    "link_hub_checked_at",
    # the link-hub check's open suggestions, which an editor accepts or dismisses in the admin
    "link_hub_findings",
    # cc by-sa 4.0, which must be credited wherever the text is shown
    "wikipedia_extract",
    "wikipedia_url",
    "wikipedia_revision",
    "wikipedia_fetched_at",
    # cc by-nc-sa, also to be credited
    "genres",
}

# the last column: a band's members, or the bands an artist belongs to
_FIELD_HEADERS = [PAGE_HEADER if name == "slug" else name for name in ACT_COLUMNS]
BAND_HEADER = [*_FIELD_HEADERS, "members"]
ARTIST_HEADER = [*_FIELD_HEADERS, "bands"]


def header(model):
    return BAND_HEADER if model is Band else ARTIST_HEADER


def act_value(act, name):
    if name == "slug":
        # a held act has no public page yet
        return "" if act.needs_review else act.get_absolute_url()
    if name == "review_reasons":
        return [MusicAct.REVIEW_REASONS.get(code, code) for code in act.review_reasons]
    return getattr(act, name)


def related_cell(act):
    """a band's members, or an artist's bands, as "Name (role)"; needs the memberships prefetched"""
    names = []
    for membership in act.memberships.all():
        other = membership.artist if isinstance(act, Band) else membership.band
        names.append(f"{other.name} ({membership.role})" if membership.role else other.name)
    return "; ".join(names)


def prefetch(queryset):
    """fetch the memberships the last column reads together, not one query per act"""
    other = "artist" if queryset.model is Band else "band"
    return queryset.prefetch_related(f"memberships__{other}")


def act_row(act):
    return [*(cell(act_value(act, name)) for name in ACT_COLUMNS), cell(related_cell(act))]
