Issue: [#57 Remove inactive bands from the public-facing Bands & Artists page](https://github.com/natea/newenglandmusic/issues/57)

## Context

`/bands` is built by `live_acts()` in `core/views/act_index.py`, which lists every `Band` and `Artist` with `needs_review=False`. `needs_review` already hides an act completely (no page, no event links, out of search and the sitemap), so it is the wrong tool: Sooz wants inactive acts to keep their pages and show links. The act admin (`MusicActAdmin`) has filters and bulk actions; the CSV export lists its columns by hand and a test fails when a new model field is neither exported nor excused.

## Goals / Non-Goals

**Goals:** leave inactive acts off the index only; let editors manage the mark; mark the 23 acts Sooz named.

**Non-Goals:** hiding acts from pages, show links, search, sitemap or the discovery deck; handling acts from outside New England; any new screen.

## Decisions

- **A boolean `MusicAct.is_inactive`** (default False, indexed), with a migration. Inactive is a different fact from "held for review", so it gets its own field rather than a new review reason.
- **Only `live_acts()` changes:** it adds `is_inactive=False`. Everything else reads `needs_review` and is left alone, which is exactly Sooz's option 2.
- **Admin:** the checkbox in the act's form, `is_inactive` in `list_filter` (not a list column), and two bulk actions. Because editors own the mark, imports (`import_artists`, `import_act_list`) and enrichment don't write it, so they can't clear it.
- **CSV export:** `is_inactive` joins `ACT_COLUMNS` so the sheet shows what editors set. Reading an exported file back in is not changed: imports ignore the column on purpose, because editors own the mark in the admin; a test checks that an exported file with the column still imports.
- **`mark_inactive_acts`:** takes slugs as arguments (or `--file` with one per line), a `--dry-run`, and `--active` to reverse. Slugs are used because names repeat across bands and artists; a bare slug is looked up among both bands and artists, and one that matches both (slugs are unique only within a kind) is reported as ambiguous and changes nothing; `bands/orbit` or `artists/orbit` names the kind. It marks acts held for review too (harmless, they're off the index already). It prints the acts it changed, the ambiguous addresses and the addresses it didn't find, and records a `JobRun` as a `RecordedCommand`. It is run by hand, not scheduled. Sooz's list gives the slugs in the thread's links (for example `aerosmith`, `til-tuesday`); the kind (band or artist) follows the link's path and is passed as the qualified form, and a slug that doesn't exist here is reported, not guessed at.
- **Search, sitemap, discovery deck and the act pages** keep including inactive acts, since links to them must work. An inactive act with an upcoming show still shows in the deck.

## Risks / Trade-offs

- The site's slugs may differ from the slugs in Sooz's links; the command reports misses so an editor can mark those in the admin.
- Searching for an inactive act still finds it. That follows from option 2, but it is a choice.

## Test mocking

No outside service is involved; tests use Django's `TestCase` and call the command with `call_command`. No network is touched.

## Open Questions

- Should inactive acts also drop out of the discovery deck and search? The thread only asks about the Bands & artists page, so this proposal keeps them in both; Sooz or Nate can say otherwise.
- The further inactive acts Sooz will share (without a MusicBrainz profile) are not yet listed; they are marked with the same command or the admin once she sends them.

## Wording note

"Live" in the index requirement means neither held for review nor inactive. Search and suggestions use it for "not held for review" only, so inactive acts still turn up there; the scenarios say which applies. The command's job run sets `job_summary` to the number of acts changed.
