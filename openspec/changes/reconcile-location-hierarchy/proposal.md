# Proposal

## Why

The editors have written one list of where every New England town belongs: `Stagehopper_Regions_v0.1.csv`, with 6 states, 50 regions, 117 sub-regions, all 1,602 towns and cities, and Boston's 19 neighborhoods. The site doesn't follow it. Today a visitor picks a state, then a "metro area" that means something different in each state: Massachusetts has the editors' 28 sub-regions in 7 groups, while the other five states have two or three county blocks from the old venue sheet ("CT: Coast", "NH: South"), and Rhode Island has none. Below that, towns and neighborhoods are whatever text each venue happens to carry.

A venue's place is also worked out afresh on every request, from rules about its town text, its county text and its OpenStreetMap neighborhood. That leaves gaps the editors' list closes:

- **Guessed towns.** A Massachusetts venue in a town the site's lists don't name is given its county's default sub-region. On the local copy of the venues, 13 of 240 Massachusetts venues sit in a different sub-region from the one the editors' list gives their town (Woburn is in MetroWest, and the list puts it in Merrimack Valley / Greater Lowell).
- **Spellings as towns.** "Allston", "Florence" and "Bellows Falls" are offered as towns beside Boston, Northampton and Rockingham, because that is what the venues' town text says.
- **Counties that no longer match.** Connecticut's venues carry the eight old counties, and the Census Bureau, and the editors' list, now use nine planning regions.

## What Changes

- **One hierarchy, for all six states.** State, region, sub-region, town, neighborhood, loaded from the editors' file, which is checked into the repository. It replaces the rule lists in `core/geo_areas.py`.
- **Each venue is placed once, and the placement is stored.** A New England venue is matched to a town in the list by its state and town text, through a list of other names ("Florence" is Northampton, "Allston" is Boston's Allston-Brighton). It then has one town, one sub-region and one region. Editors can correct a placement in the admin, and a report lists the venues that couldn't be placed.
- **The location picker follows the hierarchy.** State, then region, then sub-region, then towns, then neighborhoods. Each menu lists only what is inside the choice above it and has at least one venue. A region with one sub-region skips that menu.
- **Boston's neighborhoods come from the list.** A Boston venue's OpenStreetMap neighborhood ("Fenway-Kenmore") is matched to the listed one ("Fenway"), which decides its sub-region and is what the picker offers. Other cities keep their OpenStreetMap neighborhoods.
- **A new version of the file can be checked before it's adopted.** A command reports what would change, and which venues would move or lose their place, without changing anything.
- **Venue pages, the admin and the venue export show the same place:** the matched town, sub-region and region.
- **BREAKING: "metro area" goes away.** The `metro` URL parameter is replaced by `region` and `subregion`. Every old address keeps working: a Massachusetts sub-region's old address opens the same sub-region, and another state's old metro opens that state. Saved filters, weekly email choices and calendar feeds are carried over.
- **BREAKING: five Massachusetts sub-regions take the list's shorter names** ("Berkshires", "Hilltowns", "Pioneer Valley", "Montachusett", "Quabbin"), and about 13 Massachusetts venues move to the sub-region the list gives their town.
- **BREAKING: the admin's Region and Metro Area filters list New England only.** The areas outside New England (Tri-State, "NY: Hudson Valley" and the rest) are removed. The State filter still lists every state, so those venues are still a click away.

The line each event shows ("@ Great Scott, Allston, MA") doesn't change, and nothing is fetched from any outside service.

## Capabilities

### New Capabilities
- `place-hierarchy`: the site's own list of states, regions, sub-regions, towns and listed neighborhoods, how it is loaded and checked, and how a new version is compared before it's adopted.
- `venue-placement`: how each New England venue is matched to a town, a listed neighborhood, a sub-region and a region, how editors correct it, and how unplaced venues are reported.

### Modified Capabilities
- `event-geo-filter`: areas are the hierarchy's regions and sub-regions, a venue belongs to an area by its stored placement, the picker gains a region level and renames "metro area", towns are the list's towns, and old addresses are carried over.
- `area-calendar-feeds`: feeds take `region` and `subregion`, and a subscribed feed with an old `metro` address keeps its area.
- `new-england-scope`: the admin's area filters are Region, Sub-region and State, and only State reaches outside New England.
- `venue-export`: the file gains each venue's matched town, sub-region and region.

## Impact

- **Data:** a new checked-in file, `core/data/stagehopper_regions.csv`, and a small list of other names for towns and neighborhoods. `core/geo_areas.py` and `core/geo_area_sync.py` are replaced.
- **Schema:** new town and listed-neighborhood tables; `GeoArea` gains a parent and loses its rule lists; `Venue` gains its matched town, listed neighborhood and sub-region. One data migration rewrites stored weekly email area choices.
- **Code:** `core/geo_filters.py`, the picker template and its script, the admin's venue and event filters, the venue page's place line, `core/digest_forms.py` and `core/digest.py`, the calendar feed, `core/venue_export.py`, `sync_venues_from_gsheets` and `lookup_venue_neighborhoods` (both re-place the venues they change). `report_massachusetts_regions` is replaced by a report for all six states.
- **Other changes in flight:** `add-venue-list`, `add-venue-pages`, `add-weekly-email-digest` and `add-search-results-map` describe the metro filter. They should be archived, or brought up to date, before this one is built (see design.md).
- **No new dependency, API or cost.** The Census names and town centres in the file are public domain.
