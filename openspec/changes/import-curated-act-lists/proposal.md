## Why

The band and artist records so far come from the events' names, and only where MusicBrainz knows the act, so many of the region's local acts have no page. Sooz has a vetted list of the New England acts she plays on Oh Hello Boston ("OHB Artist Library for NE Music DB": "In Rotation", 496 rows, and "2026 backlog", 79 rows; 555 different acts, 19 of them on both tabs), with towns, websites, Bandcamp, Instagram and YouTube links, and many MusicBrainz IDs already filled in. The site can't take it today: `import_artists` needs an `Act_ID` and a `Kind` on every row and has no Instagram or YouTube columns, and no record says which list it came from, so editors can't see or filter "the acts from Sooz's sheet".

## What Changes

- **A record remembers the lists that name it.** Artists and bands gain `sources`, a list of short source keys (e.g. `ohb`), shown and filterable in the admin. An act on several lists carries each key once; importing never removes one.
- **A new command imports a curated list of names:** `import_act_list --source ohb --sheet <id> --tab "In Rotation" --tab "2026 backlog"` (or `--csv <path>`, also repeatable), reading the list in its own layout through a column map (Artist → name, City → town, State as a name or code, Website, Bandcamp, Instagram, YouTube, MusicBrainz ID, Kind). For each act:
  - with a MusicBrainz ID, that MusicBrainz artist decides the kind (a person is an artist, a group a band);
  - without one, the name is searched on MusicBrainz as the events' import does: exactly one group makes a band, exactly one person an artist; when it finds both, the list's own Kind settles it;
  - an act already on the site (same MusicBrainz ID, or the same name and kind) gets the source added and its empty fields filled; otherwise a record is made;
  - rows naming the same act, on one tab or across tabs (the same name, ignoring case, accents and punctuation, or the same MusicBrainz ID), are merged into one before anything is looked up, so the act is looked up once and becomes one record; where they disagree on a field, the first tab given wins and the disagreement is reported;
  - every act on the list becomes a record, since the list is already vetted; an act MusicBrainz can't settle cleanly (not found, several with the name, both kinds and no Kind, an ID that isn't found or names a different act, or a match placed outside the Northeast) is made anyway but **held for review**: hidden from the public site (no page, no performer links, not in the sitemap) until an editor marks it ready in the admin, as venues wait in the Places review.
  After the records, every approved event is linked to the acts its names are, as the events' import does, so existing listings and band pages pick up her acts at once.
  Fields are written only when unset or the list's own, never over an editor's or MusicBrainz's, as `import_artists` does. `--dry-run` and `--limit` work as elsewhere.
- **A review queue for acts.** Artists and bands gain a review flag and its reasons; the admin filters by "Needs review", shows the reasons, and has a "Mark ready" action, which puts the act live and links the events that name it. Acts made from events, by hand or already live are never held.
- **`import_artists` gains `Instagram` and `YouTube` columns,** filling the existing `instagram_url` and `youtube_url` fields.
- **First use:** Sooz's "In Rotation" and "2026 backlog" tabs together as source `ohb`, "In Rotation" first, locally with `--dry-run` first, then production with approval. Her Genre, "Tracks on Air", "Active?" and "First Album Decade" columns are not imported in this change.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `artist-records`: the CSV/sheet import gains Instagram and YouTube columns; records gain their sources and the admin filters by them; a new requirement for importing a curated list of names whose kind MusicBrainz decides.

## Impact

- **Model and migrations:** `MusicAct.sources` (`ArrayField` of short keys, default empty), and `needs_review` with `review_reasons`, on artists and bands.
- **Public pages and links:** band and artist pages answer 404 for an act held for review; event linking and the sitemap leave it out.
- **Code:** a new `core/management/commands/import_act_list.py` (a `RecordedCommand`), sharing `apply_values` and field-source rules with `core/artist_import.py`, and `choose_kind` and the matcher with `import_artists_from_events`; a MusicBrainz lookup by ID for the kind (`core/music_ids.py` `artist()`); the admin's source filter and column; `import_artists` reads two more columns.
- **External calls:** MusicBrainz only, about one or two requests per act at one a second (about 15 to 20 minutes for her 555 acts); Last.fm as evidence where several match, as today. No paid API.
- **Docs:** `PRODUCTION.md` (the command and its sources), `AGENTS.md`'s artists section.
