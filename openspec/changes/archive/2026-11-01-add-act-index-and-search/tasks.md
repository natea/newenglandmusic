## 1. The index

- [x] 1.1 Add `core/views/act_index.py` at `/bands` (live acts with their next show, grouped A–Z with "#", "The" ignored) and the `/artists` redirect; verify with view tests for "Bands and artists together", "A leading The and digits", "The next show", "Held acts left out" and "The artists address".
- [x] 1.2 Build `core/templates/core/act_index.html` in the band page's card style (tab, letter rail, ruled entries), and add the "Bands & artists" menu item by data migration; verify the scss test compiles and the phone scenario at 390px.

## 2. Search

- [x] 2.1 Add `core/search_kinds.py` (bands & artists, venues, shows) and use it in `core/views/search.py` and `search.html`, sections in order, names matched on their normalized form, held acts and inactive venues left out; verify with tests for "A band by name", "A venue by name" and "No act matches".
- [x] 2.2 Add `/search/suggest?q=` from the same registry (five per kind, nothing under two characters); each item carrying its kind; verify with view tests for "Suggestions by kind" and "Too short".
- [x] 2.3 Vendor accessible-autocomplete 3.0.2 (its min.js and min.css, with its licence) into `core/static/core/vendor/accessible-autocomplete/3.0.2/`, and add `core/static/core/js/search-suggest.js` mounting it on the search box in `base.html` (fetching `/search/suggest`, kind-tagged suggestion template, going to the chosen url), its stylesheet overridden in the site's look; verify "Each suggestion says what it is", "Going straight to a band", "Running the full search" and keyboard and screen-reader behavior with a Playwright browser test, and "Without JavaScript" with a plain form submission test.

## 3. Indexable pages

- [x] 3.1 Remove `noindex` from act pages and list every live act and `/bands` in the sitemap; verify with tests for both scenarios of "Act pages are found by search engines", and update the existing band-page and sitemap tests that expected `noindex` or shows-only listing.

## 4. Finish

- [x] 4.1 Run the whole suite with the network blocked and verify every scenario in this change's specs has a passing test; check `/bands` and a search on the test site at 1440px and 390px.
- [x] 4.2 Update `DESIGN.md` (the index) and `PRODUCTION.md` (the menu item, sitemap); verify both describe the shipped behavior.
