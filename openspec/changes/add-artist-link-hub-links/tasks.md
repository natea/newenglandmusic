Issue: [#29 When adding pages for new artists, or when augmenting pages for existing artists, check for and extract linktr.ee or…](https://github.com/natea/newenglandmusic/issues/29)

## 1. Research and data

- [ ] 1.1 Check the live pages of Linktree and the candidate hubs in the design (read-only, robots.txt obeyed, one page each): which give their links without JavaScript, and what their robots.txt says. Note in particular whether Linktree's robots.txt and page answer a plain client or are always "blocked"; if always, stop and ask the owner about scope. Record the final `HUBS` list in the design, and save sanitised page fixtures in `core/tests/fixtures/link_hubs/`.
- [ ] 1.2 Add `link_hub_url`, `link_hub_status`, `link_hub_checked_at` and `link_hub_findings` to `MusicAct`, with a migration. Verify with model tests and that `makemigrations --check` is clean.
- [ ] 1.3 Write `core/link_hubs.py`: `HUBS`, `hub_for`, `links_on`, `classify`, address comparison and `apply`. Write the automated tests for the scenarios "Not a page on a hub", "Filling an empty field", "Several candidates", "A video is not a channel", "The hub's own label names the website", "Protected values stay", "Not a Bandcamp address", "A link on another site", "A page with no links", "A hub address in the website field", "A hub address too long for its field", "A conflicting YouTube link", "The same address written differently", "A finding goes away" "A dismissed finding" and "A changed hub replaces its own fill".

## 2. Finding the address

- [ ] 2.1 Take a hub address from MusicBrainz's links in `artist_enrichment.links()` and `apply_details`, and from a hub address in `website` (copied by the command's pre-pass, task 3.1). Make `apply_details` and `add_introduction` leave a "link hub" value alone when MusicBrainz and Wikidata have none, and let theirs replace it when they do, and make the website/Bandcamp loop of `apply_details` replace a "link hub" value too, widen the `URL_TYPES` filter in `links()` so a hub link of any relation type is kept, and make `clear_musicbrainz` keep `link_hub_url`'s source mark. Write the automated tests for "Hub address as the website", "Hub address from MusicBrainz", "Editor's address kept", "Hub link among several links" "Clearing a match", "Enrichment keeps a hub fill" and "A hub fill is replaced by MusicBrainz" (for the website and Bandcamp as well as Instagram and YouTube), with the MusicBrainz fixture extended.

- [ ] 2.2 Make `artist_import._apply` and `act_list.fill` treat a "link hub" owner like unset, so an import row's or a curated list's value replaces a hub fill (marked "import" or the list's key). Write the automated tests for "A row replaces a hub fill" and "A list replaces a hub fill".

## 3. The command

- [ ] 3.1 Write `read_artist_link_hubs` as a `RecordedCommand` (`--limit`, `--refresh`, `--dry-run`), with the pre-pass that copies a hub address from `website` (and re-copies when the website changes and the stored address is the copy's own), robots.txt (import `robots_allows`, cache each host for the run), the existing user agent, pacing, no off-host redirect, statuses and `job_summary` and `job_problems` (act entries as in the design; change `problems_table` in `core/admin.py` to show an entry with no `venue_id` as plain text under a "records with problems" heading), writing with `update()`. Write the automated tests, with a fake session, for "A readable hub", "Robots forbids it", "A deleted hub page", "A hub that can't be read", "Recently read records are skipped", "A redirect off the hub", "One failure doesn't stop the run" "Address-only hub" and "A blocked act in the job run", including that no request goes to Bandcamp or to a blocked page.
- [ ] 3.2 Add the step to `bin/weekly.sh`, and document the command, the hub list and the rules in PRODUCTION.md and in AGENTS.md's pipeline section. Update the `WEEKLY` list in `core/tests/test_scheduled_jobs.py` and write the automated test for the modified "Weekly run" scenario (the script lists the six steps in order; a run appears as a `JobRun`).

## 4. Admin

- [ ] 4.1 Add the "Link hub" fieldset, address validation, findings display, list column and filter, and the accept and dismiss actions to `MusicActAdmin`; check the read-only status, time and findings fields never appear in the form's `changed_data`, so `save_model` doesn't mark them "editor". Write the automated tests for "Not a page on a hub" (in the admin), "Accepting a finding", "Records with findings" and the dismiss action, for an artist and a band; the admin actions write with `update()`. "Not a page on a hub" in the artist-link-hubs spec is tested here, at the admin, and at the unit level in 1.3.

## 5. Finish

- [ ] 5.1 Run the whole suite with outbound network blocked, and a real `read_artist_link_hubs --limit 5 --dry-run` against records with hub addresses, logging to `logs/read_artist_link_hubs-YYYY-MM-DD.log`. Update the design if the live pages contradict it. Verify that every scenario has a passing test.
