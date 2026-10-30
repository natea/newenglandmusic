## Why

`add-artists-and-bands` made Artist and Band records, filled from a sheet editors keep. But the site already names hundreds of acts: the Artists column of its events ("Rival Sons, The Blue Stones, The Velveteers"). Locally, 731 approved events name 948 distinct acts there. Typing them into a sheet by hand would take days. The names don't say whether an act is a person or a band, though, and that's the one thing a record needs before anything else.

## What Changes

- **A command that makes records from the events' Artists column.** `import_artists_from_events` reads the Artists column of every approved event, past and upcoming, splits it into names with the splitter the Spotify matching already uses (`core/artist_names.split_names`), skips placeholders ("TBA", "special guests") and names already a record, and asks MusicBrainz what each one is.
- **MusicBrainz decides artist or band.** Each name is searched as a person and as a group, with the matching rules enrichment uses: an exact name, and where several acts share it, evidence (a covered state, or Last.fm's page naming the MusicBrainz ID). A name that's settled as exactly one kind becomes that record, with its MusicBrainz ID, for `enrich_artists_from_musicbrainz` to fill in. Nothing is guessed.
- **Everything else goes on a review list, not into the database.** A name that's on MusicBrainz as both a person and a group, has several candidates with no evidence, or isn't on MusicBrainz at all, is written to a CSV in the import layout, with `Kind` and `Act_ID` blank and a reason and an example event for each. An editor fills those two in and runs `import_artists --csv`, so the import is where people decide.
- **Events link to their performers.** A new link from an event to each artist or band on its bill, in billing order: a multi-valued field, since one event has several acts. It sits alongside the Artists text, which stays: fetched events arrive as text, the text is the only home for a name with no record yet, and the event pages and play buttons read it today. Links are made:
  - by `import_artists_from_events`, for every approved event, once its names are records;
  - by `fetch_events`, for each event it saves, from names that already match a record;
  - by an editor, on the event's admin page, where performers are listed in order with autocomplete for artists and bands, to add, remove or reorder.

  A name links only when exactly one artist or band has it (compared normalized). Links made from the names are rebuilt when the text changes; links an editor adds are kept.
- **Repeatable.** Names already a record are skipped, so a second run only looks at new ones. `--limit` and `--dry-run` as usual.

### Not in this change

- Replacing the Artists text, or reading performers instead of it anywhere visitors see: the event pages and the Spotify, Apple Music and YouTube play buttons keep reading the text, and stay keyed by name. That's for a later change, once most names have a record.
- (Changed on 2026-10-29, after building: titles count too. Every source puts the headliner in the title and leaves it out of the Artists column, so reading only that column skipped nearly every headliner; the title splitter the Spotify matching uses drops tour and show words.)
- Splitting duo billings ("Connor Garvey & Ben Cosgrove"). The whole name is searched; if MusicBrainz doesn't know it, it goes on the review list.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `artist-records`: records can also be made from the events' Artists column, with MusicBrainz deciding artist or band, and a review list for the rest; and events link to their artists and bands, in billing order.

## Impact

- **Code:**
  - `core/artist_enrichment.py` gains a function deciding a name's kind from both searches;
  - a new `EventPerformer` model (event, an artist or a band, order, source), with a migration;
  - `core/event_performers.py`, linking an event's names to records;
  - a new `import_artists_from_events` command, recorded as a `JobRun`;
  - `fetch_events` links each event it saves;
  - the event admin's performers inline.
- **Services:** MusicBrainz (two searches a name, plus area lookups to place candidates) and Last.fm (only for shared names, nothing kept). About 950 names take roughly 35 to 60 minutes at MusicBrainz's one request a second. Free.
- **Data:** new Artist and Band records with a MusicBrainz ID and no `Act_ID`, and links from approved events to them. Events' text, pages and stored HTML don't change. Run locally first, then on Render as a one-off job, with approval, followed by `enrich_artists_from_musicbrainz`.
