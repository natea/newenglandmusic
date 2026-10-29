## Context

Artists exist today only as names: `core/artist_names.py` splits an event's title into names, and `SpotifyArtistLink`, `AppleMusicArtistLink` and `YouTubeArtistLink` are keyed by a normalized name (`core/artist_matching.normalize`). `core/music_ids.py` has a paced MusicBrainz client (1.1 s between requests, retrying 503s, the contact user agent from `core/user_agent.py`), used to read URL relationships. `core/lastfm.py` has a paced Last.fm client with `artist_info(name)`, and `core/artist_evidence.py` the rules `resolve_artists_with_lastfm` uses (a covered state from MusicBrainz's area hierarchy or a Last.fm bio; "shared name" notes in a bio). `core/google_sheets.py` and `sync_venues_from_gsheets` read a sheet tab with a service account on Render and with `gog` locally, keyed by `Venue_ID`.

## Goals / Non-Goals

**Goals:** records for artists and bands with members; a repeatable import from a sheet or CSV that editors own; MusicBrainz data stored under its licence; Last.fm and Bandcamp used only as their terms allow.

**Non-Goals:** public pages; linking events or the Spotify, Apple Music and YouTube links to records; scheduled runs; reading anything from Bandcamp; storing anything from Last.fm; Discogs or Wikidata lookups beyond storing their IDs.

## Decisions

**1. Two models on one abstract base, and a membership model.** `MusicAct` (abstract) holds the shared fields: `name`, `name_key` (normalized, indexed), `act_id` (the import's `Act_ID`, unique, nullable), `city_town`, `state`, `website`, `bandcamp_url`, `notes`, and the MusicBrainz fields: `musicbrainz_id` (unique, nullable), `musicbrainz_status` (`matched`, `ambiguous`, `not_found`, `editor`), `musicbrainz_checked_at`, `mb_type`, `country`, `area`, `begin_date` and `end_date` (MusicBrainz's partial dates, "1994" or "1994-05", kept as text), `genres` (array), `wikidata_id`, `discogs_url`. `Artist(MusicAct)` and `Band(MusicAct)`. `BandMembership(band, artist, role, begin_year, end_year, source)`, unique on `(band, artist, role)` so one person can hold two roles. Alternative rejected: one `Act` model with a kind field, which the user didn't ask for and which makes "members" a self-relation that can point at a band.

**2. Who owns which field.** Each record has `editor_fields`, an array of field names an admin has changed (set by the admin's `save_model` from the form's `changed_data`). The import writes only its columns' fields, skipping any in `editor_fields`; enrichment writes only MusicBrainz fields, and fills `website` and `bandcamp_url` only when they're empty. Memberships carry their `source`; the import adds and updates its own but never removes one, and enrichment never removes an import's or an editor's.

**3. The sheet layout.** One header row; columns `Act_ID` (required, e.g. A0001), `Name` (required), `Kind` (`artist` or `band`), `Members` (bands: `Name (role); Name (role)`), `Town`, `State` (two letters), `Website`, `Bandcamp`, `MusicBrainz_ID`, `Notes`. A CSV and a sheet tab are parsed into the same rows (`csv.DictReader`; the sheet's values to dicts by header), so one importer serves both. Members are matched to an artist with the same `name_key`, preferring one already in the band, else created without an `Act_ID`; an editor can merge duplicates in the admin later.

**4. Matching on MusicBrainz.** Search `artist` with the name, type `person` or `group`, and take candidates whose normalized name (or an alias) equals the record's `name_key`. Accept the only one; with several, accept the one whose area is in a covered state (`artist_evidence.covered_places`, following the area's "part of" links as `resolve_artists_with_lastfm` does), else the one whose MusicBrainz ID Last.fm's page gives, unless its bio has a shared-name note. A band's members come from a lookup with `inc=artist-rels+url-rels+genres` ("member of band" relationships, with their `begin`, `end` and instrument attributes as the role); a person's links from `inc=url-rels`. Each record costs one search and one lookup, about 2 s at MusicBrainz's pace: 500 records take about 17 minutes.

**5. Licensing.** MusicBrainz core data is CC0 and is stored. Genres are supplementary data (CC BY-NC-SA 3.0); they're stored, shown only in the admin, and credited "Genres from MusicBrainz (CC BY-NC-SA)". Last.fm answers live only in memory during a run. Bandcamp: only URLs, validated as `https` on `bandcamp.com` or a subdomain, never fetched.

**How it's tested.** Model tests for memberships; importer tests from a CSV string and from mocked sheet values (gog and the service account mocked) for every scenario, including the editor's field and the bad row; enrichment tests with recorded MusicBrainz JSON fixtures in `core/tests/fixtures/musicbrainz/` and a mocked Last.fm client, asserting nothing from Last.fm reaches the database and no request goes to bandcamp.com; admin tests for the inline, the hand-set ID and clearing. The suite passes with outbound network blocked.

## Risks / Trade-offs

- **[Duplicate member artists]** A member named in two bands' rows becomes one artist if the names match, but "Jon Smith" and "Jonathan Smith" become two. → MusicBrainz IDs join them where it knows both; an admin merge action is a follow-up.
- **[A wrong MusicBrainz match]** Small local acts are often missing from MusicBrainz or share names. → Only exact names of the right kind are accepted, and several candidates need evidence; the admin can set or clear the ID.
- **[MusicBrainz is slow or busy]** → The client's pacing and 503 retries; `--limit` for batches; a stopped run keeps what it saved.

## Migration Plan

Migrate. Make the sheet in the layout above, import it with `--dry-run` first, then for real; then run the enrichment with `--limit 20 --dry-run`, check the matches, and run it for the rest. Nothing runs on a schedule yet.

## Later

**Bandcamp's embedded player**, with the public pages. Bandcamp's "Share / Embed" code is an iframe from `bandcamp.com/EmbeddedPlayer/album=<id>/...` (or `track=<id>`). An editor or the act pastes it; the site keeps only the album or track ID, validated as digits, and renders Bandcamp's player itself, so no pasted HTML is stored or shown. Bandcamp serves the player and its music, and no request is made to Bandcamp to find the ID. Nothing in this change depends on it.

## Open Questions

- Should a membership's role be a free text field, or chosen from a list of instruments? (Free text here; MusicBrainz's instrument names fit it.)
