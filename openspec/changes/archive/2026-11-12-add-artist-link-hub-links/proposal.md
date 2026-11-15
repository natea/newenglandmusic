Issue: [#29 When adding pages for new artists, or when augmenting pages for existing artists, check for and extract linktr.ee or…](https://github.com/natea/newenglandmusic/issues/29)

## Why

Small acts often put everything in one link-hub page (Linktree and its rivals) long before they have a website or a streaming profile. The site already recognises these addresses, but only when it checks a venue: `check_event_sources` calls them "social-only" and gives up. An artist's or band's record has nowhere to keep one, so the links inside (Bandcamp, Instagram, YouTube, the act's own site) never reach the record. Issue #29 asks for the pipeline to find those pages and use what's in them; the owner of the issue chose to read the page's links, fill gaps, and flag disagreements for review.

## What Changes

- **A record keeps a link-hub address,** found from the record's own website when that is a hub address, from MusicBrainz's links when one is a hub address, or typed in by an editor in the admin.
- **A new command, `read_artist_link_hubs`,** reads each record's hub page (politely: robots.txt, the honest user agent, one request a second, no JavaScript, no redirects followed) and takes the links it can classify by their address: website (only when the hub labels it so), Bandcamp, Instagram and YouTube.
  - A link for a field the record **has empty** fills it, marked as "link hub" in `field_sources`.
  - A link that **differs** from what the record has is not applied: it is saved as a finding for an editor to review in the admin (accept or dismiss). Dismissed findings stay dismissed.
  - An editor's, the import's, MusicBrainz's and Wikidata's values are never overwritten. A hub address in the record's `website` stays where it is (it is copied to the hub address, and a real site found on the hub is saved as a finding).
  - A value this command filled earlier is the one exception: a later read that finds a different single link replaces it, since the site set it itself. MusicBrainz's or Wikidata's value, when enrichment finds one, replaces it too.
- **Supported hubs:** Linktree plus the most common alternatives (a first list is in the design; it is confirmed against the live sites while building). A hub the site can't read (its links are built by JavaScript) keeps its address only, and the record says so.
- **Weekly job:** the command runs in `bin/weekly.sh`, after the venue steps, so new and refreshed records are picked up without extra steps. It is recorded as a `JobRun`.

### Not in this change

- Searching the web, or guessing a handle from an act's name, to find a hub page nobody linked (a wrong guess would put another act's page on a record).
- Storing links the records have no field for (Spotify, Apple Music, TikTok, Facebook, ticket links), or reading the hub's titles, bio or images.
- Event or venue pipelines: venue checks keep treating a hub address as "social-only".
- Showing the hub address on the act's public page (an open question in the design).
- Finding hubs for new artists automatically: enrichment and the artist import are run by hand, so only the weekly read is scheduled (an open question in the design).
- Bandcamp is still never requested; a Bandcamp link is stored as an address only.

## Capabilities

### New Capabilities
- `artist-link-hubs`: finding an act's link-hub address, reading the page, filling gaps, flagging conflicts, and the admin review.

### Modified Capabilities
- `artist-records`: records keep a hub address, MusicBrainz's hub links are taken during enrichment, a link hub is a fourth source of a Bandcamp URL, and enrichment leaves hub-filled links alone unless it has a value of its own, and the two imports treat a hub-filled link as unset.
- `scheduled-jobs`: the weekly job runs a sixth command.

## Impact

- **Code:** `MusicAct` gains `link_hub_url`, `link_hub_status`, `link_hub_checked_at` and `link_hub_findings`, with a migration; a new `core/link_hubs.py` (hosts, fetching, parsing, applying); the command `read_artist_link_hubs`; `artist_enrichment.links()` takes a hub link, and `apply_details` and `add_introduction` leave hub-filled links alone; `import_artists` and `import_act_list` replace them; the job-run page shows an act's entry; the admin shows the fields, the findings and review actions; `bin/weekly.sh`, the weekly-job test, PRODUCTION.md and AGENTS.md mention the step.
- **Services:** the hub sites themselves (free, no key), one page per record, at most weekly. No paid API.
- **Rules kept:** robots.txt obeyed; nothing from Bandcamp requested; no key involved.
