## 1. The index

- [ ] 1.1 Add `core/views/act_index.py` at `/bands` (live acts with their next show, grouped A–Z with "#", "The" ignored) and the `/artists` redirect; verify with view tests for "Bands and artists together", "A leading The and digits", "The next show", "Held acts left out" and "The artists address".
- [ ] 1.2 Build `core/templates/core/act_index.html` in the band page's card style (tab, letter rail, ruled entries), and add the "Bands & artists" menu item by data migration; verify the scss test compiles and the phone scenario at 390px.

## 2. Search

- [ ] 2.1 Add acts to `core/views/search.py` and `search.html` (unaccented name match, live acts, up to 20, above events); verify with tests for "A band by name" and "No act matches".

## 3. Indexable pages

- [ ] 3.1 Remove `noindex` from act pages and list every live act and `/bands` in the sitemap; verify with tests for both scenarios of "Act pages are found by search engines", and update the existing band-page and sitemap tests that expected `noindex` or shows-only listing.

## 4. Finish

- [ ] 4.1 Run the whole suite with the network blocked and verify every scenario in this change's specs has a passing test; check `/bands` and a search on the test site at 1440px and 390px.
- [ ] 4.2 Update `DESIGN.md` (the index) and `PRODUCTION.md` (the menu item, sitemap); verify both describe the shipped behavior.
