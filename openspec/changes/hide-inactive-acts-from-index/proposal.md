Issue: [#57 Remove inactive bands from the public-facing Bands & Artists page](https://github.com/natea/newenglandmusic/issues/57)

## Why

Many acts imported from Sooz's Oh Hello Boston list are no longer active, yet the public Bands & artists page at `/bands` lists them. Sooz asked (issue 57) for inactive acts to be left off that page. Asked whether they should vanish completely or only leave the list, Sooz chose the second: their own pages and the links from shows keep working.

## What Changes

- Add an **inactive** mark to bands and artists (`MusicAct.is_inactive`, default off). It is separate from `needs_review`, which hides an act everywhere until an editor accepts it.
- The `/bands` index leaves out inactive acts. Nothing else changes for them: act pages, links from past and upcoming shows, search and the sitemap behave as now; the CSV export gains a column for the mark.
- Editors set or clear the mark in the admin: a checkbox on the act, a list filter (not a list column), and bulk actions "Mark inactive" and "Mark active".
- A management command, `mark_inactive_acts`, marks acts by their page address (slug, or `bands/slug` / `artists/slug` to name the kind), with `--dry-run`, and reports any address it can't find or that matches both a band and an artist (marking neither). It is run by hand once with the 165 acts Sooz has listed so far: 23 with a MusicBrainz profile (Aerosmith through The Upper Crust) and 142 more without one, which her helper checked for recent activity and she confirmed one by one (28 Degrees Taurus through Zola Turn). Their addresses, with the kind each link's path gives, are in `inactive-acts.txt` beside this proposal, ready for `--file`.
- Imports and enrichment never clear the mark.
- Acts from outside New England are a separate question Sooz will raise on her own; they stay listed. Any further acts she shares are handled with the same tools, without a new change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `act-index`: the index leaves out inactive acts.
- `artist-records`: acts carry an inactive mark that editors set, and that imports never clear; the admin filters by it; a command marks acts by address.
- `act-export`: each row of the CSV export says whether the act is inactive.

## Impact

- `core/models.py` (new field and migration), `core/views/act_index.py`, `core/admin.py`, `core/act_export.py` (new column), a new command in `core/management/commands/`, and `AGENTS.md`'s artists section.
- No new screens, so no design step. No outside service is called.
