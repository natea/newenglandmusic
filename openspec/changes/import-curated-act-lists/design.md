## Context

- `core/artist_import.py` (`import_artists`) keys rows by `Act_ID`, needs `Kind`, and writes a field only when it's unset or its own (`MusicAct.field_sources`, source `import`). Its `apply_values` and the field-source rule are the reusable part.
- `import_artists_from_events` decides a name's kind with `choose_kind(name, matcher)` (`core/artist_enrichment.py`): MusicBrainz searched as a person and as a group, Last.fm as evidence among several. `core/music_ids.py` has `artist(mbid)` for a lookup by ID.
- `MusicAct` already has `website`, `bandcamp_url`, `instagram_url`, `youtube_url`, `city_town`, `state`, `musicbrainz_id`; `genres` and `place_review_reasons` show the project's `ArrayField` use.
- Sooz's sheet: "In Rotation" (496 rows, one act listed twice) and "2026 backlog" (79 rows, 19 of them also on "In Rotation"), 555 different acts, both with columns Artist, Genre, City, State (full names), Tracks on Air, Active?, Website, Bandcamp, Instagram, YouTube, Kind, MusicBrainz ID, First Album Decade.

## Goals / Non-Goals

**Goals:** her acts become records with their links and towns, marked as hers, without duplicating acts the events already made; the same command serves the next curated list.

**Non-Goals:** importing Genre, "Tracks on Air", "Active?" or "First Album Decade"; members (her sheet has none; enrichment adds them from MusicBrainz); making records for names MusicBrainz can't settle.

## Decisions

### 1. `sources` as an array of short keys on `MusicAct`
`sources = ArrayField(CharField(max_length=16), default=list, blank=True)`, with a GIN index for the admin filter. Keys are short and stable (`ohb`); a mapping in `core/act_sources.py` gives each its label ("Oh Hello Boston") for the admin.
*Alternative:* a `Source` model with a many-to-many. Rejected: one more table and join for what is a handful of tags; the array filters with `sources__contains`.
*Alternative:* an `Act_ID` prefix ("OHB0001"). Rejected: a record made from events and then named by her list has no Act_ID to give, and a record can be on two lists.

### 2. A separate command, not more `import_artists` options
`import_act_list` reads a list in its own layout through a column map (case-insensitive header aliases: `Artist`/`Name`, `City`/`Town`, `MusicBrainz ID`/`MusicBrainz_ID`), and matches by MusicBrainz ID, then by name and kind. `import_artists` stays the editor's exact-layout tool keyed by `Act_ID`, and only gains the two link columns.
*Alternative:* teach `import_artists` to accept rows without `Act_ID`. Rejected: it would weaken the key that makes re-imports safe for editors' sheets.

### 3. Rows are merged into acts before any lookup
All tabs are read first, in the order given, and rows are grouped by `normalize(name)` (the same normalization `name_key` uses, which also drops a leading "The"), joining groups that share a MusicBrainz ID. Each group becomes one act: per field, the first non-empty value in tab order, with any later different value reported as a conflict ("2026 backlog gives a different Instagram for Adam Sherman; kept In Rotation's"). So the 575 rows become 555 acts, each looked up once, and the review CSV lists each name once.
*Alternative:* import tab by tab and rely on finding existing records. Rejected: it works for records but looks each shared act up twice, and a name MusicBrainz can't settle would land on the review list twice.

### 4. How the kind is decided
- With an ID: `artist(mbid)` and its `type`: `Person` makes an artist; `Group`, `Orchestra` and `Choir` make a band; anything else, or an ID MusicBrainz doesn't know, goes to review.
- Without: `choose_kind(name, matcher)`. When it returns "both a person and a group" and the row's `Kind` is artist or band, that kind's MusicBrainz candidate is taken; otherwise the reason goes to review. Her Kind never overrides a single clear MusicBrainz answer.

### 5. Finding before making
A record with the same MusicBrainz ID (either kind) is the act, so a mismatched kind is reported, not duplicated; else a record of the decided kind with the same `name_key`. A found record gets the source added, and its unset or list-owned fields filled; its name is not changed. Field sources are recorded as the list's key (`ohb`), so a later run of the same list can update its own values and never an editor's.

### 6. State names
A map of the US state names (and DC) to their codes; a value already two letters passes through; anything else is reported and left out.

## Risks / Trade-offs

- [A name search picks the wrong same-named act] → the same rules as the events' import (exact name or alias; Last.fm evidence among several); every made record shows "ohb" so an editor can review her acts as a set.
- [MusicBrainz's rate limits] → one request a second, and the busy-wait retries the events' import already has; a stopped run keeps what it made and resumes cleanly.
- [Sooz's sheet changes later] → re-running is safe: found by ID or name, only list-owned fields change.

## Migration Plan

1. Migration adds `MusicAct.sources` (empty for all existing records).
2. Run locally with `--dry-run`, then for real, then `enrich_artists_from_musicbrainz` for the new records; share the counts.
3. On production, with approval: the same import against the production database, then enrichment.
4. Rollback: delete records whose only source is `ohb` and that no event links to, or restore the pre-run backup.
