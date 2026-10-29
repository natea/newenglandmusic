## 1. Models

- [x] 1.1 Add the abstract `MusicAct` with the shared and MusicBrainz fields and `field_sources`, `Artist`, `Band` and `BandMembership` (role, years, source, unique on band, artist and role), with a migration. Verify with model tests for an artist in two bands and a former member, and that `makemigrations --check` is clean.

## 2. Import

- [x] 2.1 Add `core/artist_import.py`: parse the layout's rows from a CSV file or from sheet values, parse `Members` with roles, validate `Kind`, `State` and the Bandcamp URL, and create or update records and memberships without overwriting a field an editor or MusicBrainz set (`field_sources`) or removing memberships. Verify with tests for importing a band with members, importing twice, the editor's change kept, a bad row, and an invalid Bandcamp URL.
- [x] 2.2 Add the `import_artists` command (`--csv`, or `--sheet` and `--tab`, and `--dry-run`), reading sheets as `sync_venues_from_gsheets` does, recorded as a `JobRun`. Verify with tests with `gog` and the service account mocked, and the dry run saving nothing.

## 3. MusicBrainz enrichment

- [x] 3.1 Add artist search and lookup (`inc=artist-rels+url-rels+genres`) to the MusicBrainz client, with recorded fixtures in `core/tests/fixtures/musicbrainz/`. Verify with client tests for the request's paths, pace and user agent.
- [x] 3.2 Add matching: exact name or alias of the right type; with several candidates, a covered area, then Last.fm's MusicBrainz ID without a shared-name note; else ambiguous or not found. Verify with tests for a clear match, a shared name, a covered area, Last.fm picking one, and no Last.fm key.
- [x] 3.3 Add the `enrich_artists_from_musicbrainz` command (`--limit`, `--refresh`, `--dry-run`, a `JobRun`): store the fields and links, keep a record's own website and Bandcamp URL, look up a given ID instead of searching, and add members, matching them by MusicBrainz ID, then name, else creating them. Verify with tests for each enrichment scenario, that nothing from Last.fm is saved, and that no request goes to Bandcamp.

## 4. Admin

- [x] 4.1 Add `Artist` and `Band` admins: list columns, filters by state and status, name search, memberships inline on both, `field_sources` marking changed fields as the editor's, setting the MusicBrainz ID by hand (status "editor"), a "clear MusicBrainz match" action, and the genres' credit. Verify with admin tests for the inline, a hand-set ID surviving `--refresh`, and clearing.

## 5. Docs and check

- [x] 5.1 Document the sheet layout, the two commands, and what may be stored from MusicBrainz, Last.fm and Bandcamp in PRODUCTION.md, and list MusicBrainz and Last.fm uses in AGENTS.md. Run the whole suite with outbound network blocked. Then, with approval, import a small sample sheet and run the enrichment with `--limit 20 --dry-run` locally, and check its matches by hand.

## 6. Introductions from MusicBrainz and Wikipedia

- [x] 6.1 Add `disambiguation`, `wikipedia_extract`, `wikipedia_url`, `wikipedia_revision` and `wikipedia_fetched_at` to `MusicAct`, with a migration. Store MusicBrainz's disambiguation in enrichment. Verify with an enrichment test using the recorded fixture.
- [x] 6.2 Add `core/wikipedia.py`: the English article's title for a Wikidata ID, and an article's summary, paced, with the contact user agent; record fixtures in `core/tests/fixtures/wikipedia/`. Verify with client tests for the requests, the user agent and the pace.
- [x] 6.3 After a match with a Wikidata ID, fetch and store the opening paragraph as the design says, accepting only an ordinary article of that Wikidata item, removing earlier text when there's none, and reporting a failure without failing the match. Show it in the admin with its credit. Verify with tests for an act with an article, one without, the wrong article, a failed request, no image stored, and the credit in the admin.
- [x] 6.4 Document the Wikipedia text and its credit in PRODUCTION.md, run the whole suite with outbound network blocked, and run the sample enrichment's dry run again to check the introductions by hand.
