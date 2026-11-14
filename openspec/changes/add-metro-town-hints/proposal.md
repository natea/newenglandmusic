## Why

The Metro Area menu names Massachusetts's 28 sub-regions ("Inner West Suburbs", "Montachusett / North County"), but not what they cover, so a visitor has to guess which one holds their town. The browser's own menu can't show a preview as the pointer moves over an option (Chrome and Safari draw it as a system menu, and phones have no hover), so the towns need to be shown where the browser allows.

## What Changes

- **The chosen metro shows what it covers,** in a line under the Metro Area menu: the towns the editors listed for a Massachusetts sub-region ("Brookline, Newton, Watertown, Arlington, Belmont, Waltham"), its neighborhoods for Boston's sub-regions, and the counties for other states' metros ("Cheshire, Hillsborough, Merrimack, Rockingham, Strafford and Sullivan counties"). On the listing and the discovery deck alike, with or without JavaScript.
- **Each metro option carries the same text as a tooltip** (`title`), which browsers that draw their own menu list (Firefox) show on hover; the others ignore it, harmlessly.
- **Each sub-region keeps the editors' wording** for this text in `core/geo_areas.py` (a new `covers` entry), so aliases kept only for matching ("manchester" beside "manchester-by-the-sea", "fenway-kenmore") don't show.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `event-geo-filter`: the Metro Area menu shows what the chosen metro covers, and each option has it as a tooltip.

## Impact

- **Code:** `core/geo_areas.py` (a `covers` text per Massachusetts sub-region), `GeoArea` (a `covers` field, one migration), `core/geo_area_sync.py`, a `covers_text` for metros without one (their counties, else towns), `core/templates/core/geo_filter_form.html`, `core/static/core/scss/geo_filter.scss`.
- **Depends on** `add-massachusetts-regions` (built and deployed, not yet archived), whose sub-regions and `event-geo-filter` requirements this builds on; archive that change first.
- **No external services,** no cost.
