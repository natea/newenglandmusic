## 1. Data

- [x] 1.1 Add `slug`, `instagram_url`, `youtube_url`, `photo_file`, `photo_author`, `photo_license` and `photo_license_url` to `MusicAct`, with a migration that backfills unique slugs. Verify with model tests for slugs (collisions get `-2`) and that `makemigrations --check` is clean.
- [x] 1.2 Extend `core/wikipedia.py`: one Wikidata call for claims and sitelinks (P18, P2003, P2397), and Commons' licence and author for a file, accepting only free licences; record fixtures in `core/tests/fixtures/wikipedia/`. Verify with client tests for a free file, a non-free one, a missing image, and the user agent and pace.
- [x] 1.3 Store photos and social links in `enrich_artists_from_musicbrainz`, from Wikidata and MusicBrainz's links, keeping an editor's. Verify with tests for each artist-records scenario, and show and edit the fields in the admin.

## 2. The page

- [x] 2.1 Add the views, URLs and `band.html` (band and artist variants) with `band.scss`, built to the direction contract and the chosen sketch: tab, name, meta line, next-show strip, fields, bio with credit, show list, invitation, `noindex` without upcoming shows. Verify with view tests for every band-pages scenario except linking from events.
- [x] 2.2 Link performers in the calendar's event listings, re-baking events whose links change, and add band and artist pages with upcoming shows to the sitemap. Verify with a calendar test for a linked performer and a plain name, and a sitemap test.

## 3. Check and finish

- [x] 3.1 Render a full band, a sparse band and an artist at 1440 and 390 wide with Playwright: no sideways scroll, next show in the first screen, images with alt text. Run Impeccable's detector on the new template and stylesheet, then its finish review against the direction contract, and record DESIGN.md with its documenter.
- [x] 3.2 Document the pages, the photo and licence rules and the invitation in PRODUCTION.md. Run the whole suite with outbound network blocked. Verify that it passes.
