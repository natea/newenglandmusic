Issue: [#28 Add CSV export button to the artists and bands roster/listing](https://github.com/natea/newenglandmusic/issues/28)

## Context

`VenueAdmin` has an export button (spec `venue-export`): a `get_urls` route `export-csv/`, a `changelist_view` that passes `can_export`, and `export_csv_view` that streams CSV from `get_changelist_instance(request).get_queryset(request)` so search, filters and order apply to every page. Columns live in `core/venue_export.py` with a `NOT_EXPORTED` set and a test that every model field is decided. The button is rendered by `admin/core/venue/change_list.html`.

The artist and band lists are `ArtistAdmin` and `BandAdmin`, both subclasses of `MusicActAdmin` over the abstract `MusicAct` model (`core/models.py`). The issue's "roster/listing" is read as these admin lists, as the venue button is on the admin's venue list.

## Goals / Non-Goals

**Goals:** the same button and behaviour on both lists; one implementation shared through `MusicActAdmin`; no model change.
**Non-Goals:** exporting from the public `/bands` index; exporting events or memberships as separate files; importing the file back.

## Decisions

- **Shared view.** Move the view body into `MusicActAdmin` (export route named `core_artist_export_csv` / `core_band_export_csv` from the model name, as the venue's is). To avoid copying it, share the streaming code with the venue view in a small helper; the venue behaviour and its tests must stay unchanged.
- **Columns by hand** in `core/act_export.py`: `ACT_COLUMNS` plus a `kind`-specific last column (`members` for bands, `bands` for artists), and `NOT_EXPORTED`. A test over `Artist._meta.concrete_fields` and `Band._meta.concrete_fields` fails for undecided fields.
- **Left out:** `id`, `name_key`, `field_sources`, `created_at`, `updated_at`, `musicbrainz_checked_at` (bookkeeping); `wikipedia_extract`, `wikipedia_url`, `wikipedia_revision`, `wikipedia_fetched_at` (CC BY-SA needs credit beside the text, which a spreadsheet column can't give); `genres` (CC BY-NC-SA, same reason). Kept: photo file, author, licence and licence URL (the credit travels with them), and the MusicBrainz ID, so anyone can look the rest up at the source. Nothing from Last.fm is stored, so nothing from it can leak; Bandcamp appears only as the page URL already stored.
- **Held acts included** (`needs_review` and its reasons shown, reasons as their readable text), since the admin list shows them and the export mirrors the list.
- **Members cell:** `Name (role)` joined with "; ", in membership order, former members marked by their end year is not added; roles only. Fetched with `prefetch_related` to avoid a query per act.
- **Formatting** reuses `cell()` and `guard()` from `core/venue_export.py` (booleans "yes"/"no", lists joined with "; ", BOM, streaming).
- **Permission:** `has_view_permission(request)` for that model, as for venues; the change-list template for each kind shows the button only when `can_export`. Add `admin/core/artist/change_list.html` and `admin/core/band/change_list.html` extending the shared template, or one shared template.
- **Filename:** `artists-<date>.csv` / `bands-<date>.csv`.

## Testing and outside services

No outside service is called: the export reads only the local database. Tests are Django `TestCase`s with no network, as `test_venue_export.py` does, and build acts directly; nothing needs a mock for Google Sheets, Anthropic, ticketing APIs, MusicBrainz, Wikipedia or Last.fm, since no fetch command runs.

## Risks

- Moving shared code could change the venue export; its existing tests guard that.
- Licensed text slipping into the file via a later new field: covered by the field-coverage test.

## Open Questions

- Where should the button be: the admin lists (assumed, as with venues) or also the public Bands & artists index? The issue says "roster/listing" and "similar to the venue export", which is in the admin.
- Should MusicBrainz genre tags and the Wikipedia introduction be included with a credit line (for example a trailing credit column or header note)? Left out until Nate decides.
- Should a band's former members be marked in the members cell, and should the export be one combined file of artists and bands rather than two? Assumed two files, no marking.
