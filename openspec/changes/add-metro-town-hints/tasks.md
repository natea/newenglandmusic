# Tasks

## 1. The covers text

- [ ] 1.1 Add `covers` to `GeoArea` with a migration, and to `core/geo_area_sync.py`'s fields; verify `makemigrations --check` is clean.
- [ ] 1.2 Add each Massachusetts sub-region's `covers` to `core/geo_areas.py` in the editors' words, and a `covers_text` that falls back to counties, then towns; verify "The editors' words stay in step with the matching" with a data test, and the fallback with a unit test.

## 2. The form

- [ ] 2.1 Render the covers line under the Metro Area menu and a `title` on each option, styled in `geo_filter.scss`; verify "A sub-region's towns", "A Boston sub-region's neighborhoods", "A metro matched by county", "No metro chosen", "Tooltips on the options" and "The discovery deck" with view tests.
- [ ] 2.2 Check the form at 1440px and 390px with a long covers line (Merrimack Valley), and in Firefox for the tooltip.

## 3. Finish

- [ ] 3.1 Run the whole suite with the network blocked; mention the covers text in `PRODUCTION.md`'s Areas section.
