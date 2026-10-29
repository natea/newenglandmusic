## Context

`Event.artists` is free text (`CharField`, 255). `core/artist_names.py` splits it (`split_names`: commas, semicolons, "w/", "x", "feat.", " + "; never "&" or "and") and cleans each name (`clean_name` drops "(DJ Set)", "(21+)" and a subtitle after a spaced dash). `is_placeholder` rules out "TBA", "special guests" and the like. `Event.objects` is approved events only. `core/artist_enrichment.Matcher.choose(record)` searches one kind (`SEARCH_TYPES[type(record)]`), keeps exact names or aliases of that kind, and picks among several by a covered state, then Last.fm, returning `(status, mbid)`. `MusicAct.save` sets `name_key` with `normalize`. The import reads extra CSV columns harmlessly (`rows_from_csv` keeps them; `import_row` reads only its own).

## Goals / Non-Goals

**Goals:** a record for every act the events name that MusicBrainz can settle as one kind, and a list of the rest for an editor, without guessing.

**Non-Goals:** replacing the Artists text, or showing performers to visitors; names from titles; splitting duos; a scheduled run.

## Decisions

**1. Decide the kind from both searches.** A new `choose_kind(name, matcher)` builds unsaved `Artist(name=…)` and `Band(name=…)` (with `name_key` set as `save` would) and calls `matcher.choose` on each. Then:
- a group matched and the person search found no exact candidate → Band;
- a person matched and the group search found none → Artist;
- both matched → review, "both a person and a group";
- either ambiguous → review, "several with this name";
- neither found → review, "not on MusicBrainz".

A record without a state skips enrichment's "placed only outside the US" check, which is right here: touring acts play local venues. Alternative rejected: deciding by the name's form ("The …" or plural for a band), which is wrong too often ("The Weeknd", "Bon Iver").

**2. Records carry only the name and the MusicBrainz ID.** A made record has `musicbrainz_id` set with `field_sources["musicbrainz_id"] = "musicbrainz"` and an empty status, so `enrich_artists_from_musicbrainz` looks it up by ID (no second search) and fills in everything else. Keeping the two steps apart keeps this command to searches, and lets the enrichment run be repeated on its own.

**3. Names, counted.** One pass over `Event.objects.exclude(artists=None)`: `split_names`, then drop placeholders, keeping for each normalized name its first spelling, its event count and its first event (venue and date). Names whose `name_key` is already an Artist's or Band's are dropped before any request. Most-named first, so `--limit` covers the acts that matter most.

**4. The review list is an import file.** Columns: the import layout (`Act_ID`, `Name`, `Kind`, `Members`, `Town`, `State`, `Website`, `Bandcamp`, `MusicBrainz_ID`, `Notes`) plus `Reason`, `Events` and `Example_Event`. Only `Name` and the three extra columns are filled: a name on the list has no single MusicBrainz artist to suggest. The default path is `logs/artists-from-events-review-YYYY-MM-DD.csv`, the run's output kept with the logs; `logs/*.csv` is in `.gitignore`.

**5. Pace and stopping.** The existing paced client (`MusicIds`, 1.1 s between requests). Each name costs two searches and, for candidates with areas, area lookups (cached per run). `MusicBrainzBusy` stops the run; records made so far are kept, each saved as it's decided, and the next run skips them.

**6. `EventPerformer`, not two many-to-many fields.** `EventPerformer(event, artist (nullable), band (nullable), order, source)`, with a check constraint that exactly one of `artist` and `band` is set, and unique constraints on `(event, artist)` and `(event, band)`. One table keeps one billing order across artists and bands, which two `ManyToManyField`s (`Event.artists_linked`, `Event.bands_linked`) couldn't. Alternative rejected: a generic foreign key, which the admin's autocomplete and Django's constraints handle poorly. `source` is `names` or `editor`.

**7. Linking from the names.** `core/event_performers.link_from_names(event, records=None)`: `split_names(event.artists)` minus placeholders, each looked up by `name_key` in a map of every artist's and band's `name_key` to its record, built once per run (names with two records map to none). It deletes the event's `names` links and creates the new ones, in order, skipping a record the event already has from an editor; `order` follows the names, and editor links keep theirs. `import_artists_from_events` calls it for every approved event after making records (a few thousand inserts, in one transaction); `fetch_events.save_event` calls it after `event.save()`, outside a dry run. Nothing reads the links for visitors yet, so stored event HTML isn't re-rendered.

**8. The admin.** An `EventPerformerInline` (tabular, ordered by `order`) on `EventAdmin`, with `autocomplete_fields = ("artist", "band")` (both admins already have `search_fields`) and `source` read-only; `save_formset` marks new rows `editor`. An editor who removes a link from names sees it come back if the name stays in the text: removing the name from the text is how to unlink it, which the inline's help text says.

**How it's tested.** With `core/tests/musicbrainz_fixture.FakeMusicBrainz` and `FakeLastFm`: a band, a person, both, not found, several without evidence, placeholders and repeats and existing records skipped, unapproved events ignored, the dry run, the review CSV's columns, a busy MusicBrainz stopping the run, and the review CSV imported by `import_artists` (with `Act_ID` and `Kind` filled in). For the links: several acts in order, a name with no record, two records with one name, the text changing, an editor's performer kept, the constraint on artist-or-band, `fetch_events` linking a saved event (and not in a dry run), and the admin inline adding an editor's performer. Nothing reaches the network.

## Risks / Trade-offs

- **[A same-named act]** A local act sharing an exact name with the only MusicBrainz act of one kind gets that act's ID. → The same risk the Spotify matching takes; an editor clears it in the admin, and the review list catches every name with two candidates.
- **[Duo billings and odd entries]** "Dana and Alden", "Cooking Class x No Stupid Questions" → whole names that MusicBrainz doesn't know go on the review list; the splitter already breaks "x" and "w/".
- **[An editor's removed link comes back]** A link made from a name is rebuilt from the text. → Removing the name from the text unlinks it, as the inline's help text says; an "unlinked" list is a follow-up if it's needed.
- **[Run time]** About an hour for 950 names. → `--limit`, most-named first; a stopped run resumes where it left off.

## Migration Plan

Run locally with `--dry-run --limit 50`, check the decisions, then without `--dry-run`; then `enrich_artists_from_musicbrainz`. On Render, with approval, as one-off jobs in the same order.
