Issue: [#159 Porchfest events should represented as multi-day festivals](https://github.com/natea/newenglandmusic/issues/159)

# Design

## Context

- Events are `Event` rows with a venue, a `starttime` and free-text `title` and `artists`; there is no group of shows above them. `Event.objects` returns approved events only; `Event.all_objects` returns all.
- The home listing and month archives (`core/views/index.py`) fetch events in a window, group them by New York date and render each one's stored HTML (`baked_html_template`). Anything an event row shows must be re-rendered when it changes.
- Venues and acts have readable slugs and pages (`/venues/<slug>`, `/bands/<slug>`); events have `/event/<id>`. The sitemap lists the home page, month archives, static pages and act pages.
- `Event.save()` re-bakes its row. Imported events are saved by `fetch_events` (unapproved), keyed by `external_id`.
- Editors' choices are protected elsewhere with a "set by" marker (`kind_set_by`), the pattern reused here.

## Goals / Non-Goals

**Goals:**
- A `Festival` with title, dates, description and slug, editable in the admin.
- A page per festival, and one multi-day entry in the calendar listing.
- Automatic attachment of shows by dates and name or town, with editor override that always wins.

**Non-Goals:**
- Festival images, venues lists, maps, ticket links or sponsor fields; the request names title, dates and description only.
- Hiding, merging or collapsing a festival's individual shows in the listing.
- Festival entries in calendar feeds (`.ics`), the weekly email or search.
- Fetching festivals from outside sources.
- Fuzzy or AI matching; matching is plain text and dates.

## Decisions

1. **Model.** `Festival(title, slug, start_date, end_date, description, match_words, town)`, with dates as `DateField` (a festival is days, not instants). `match_words` is optional, comma separated text; empty means the title. `town` is optional. `Event` gains `festival` (nullable `ForeignKey`, `SET_NULL`) and `festival_set_by` (`""` automatic, `"admin"`), plus a way to say "editor says none": `festival_set_by="admin"` with `festival=NULL`. Deleting a festival would leave editor-attached shows in exactly that state, so a pre-delete step resets `festival_set_by` to `""` for its shows and re-bakes their rows (`SET_NULL` runs no `Event.save()`). Alternatives: a separate boolean (more states to keep consistent), a many-to-many (a show belongs to one festival in practice).
2. **Matching lives in `core/festivals.py`**, a small function `festival_for(event)` that returns the festival or None, plus `rematch(event)` and `rematch_festival(festival)`. Dates are compared in New York time (`NYCTZ`), because the site's days are New York days; a 11:30pm show must stay on its own date. Words are matched as case-insensitive substrings of title, artists and venue town. Substring matching is crude ("Porchfest" would match "Porchfest preview" on a festival day, which is correct, but a short word could over-match), so the admin help text asks for distinctive words and editors can override.
3. **When it runs.** In `Event.save()` for events whose `festival_set_by` isn't `"admin"`, computing the festival before `super().save()`, so the bake in the same save already sees it and nothing re-enters matching (`rebake_html()` calls `save()`, so re-baking after an `update()` would loop). Rows of other events are rebuilt with `update(baked_html_template=...)`, the pattern in `core/event_performers.py`. `Venue.save()` re-bakes every event through `Event.save()`, so a venue save also re-matches its events (a venue town change can move a show in or out of a festival), at one extra query per event. `queryset.update()` calls in the admin skip matching; `match_festivals` fixes any drift. Bulk matching uses `select_related("venue")`. A show with no start time is never attached. On a festival save, `rematch_festival` re-evaluates events in its old and new date ranges using bulk queries, not per-event saves, and re-bakes only changed rows. `match_festivals` runs the same code over everything, so a festival created after its shows are imported can be applied with `--dry-run` first.
4. **Calendar entry.** The view fetches festivals overlapping the window with one query, picks the first covered day on screen for each, and puts the entry in that day's data next to its events. The template draws it above the day's events; it isn't an `Event` and never appears in feeds. The area filter hides a festival whose shows are all outside the area (decided by its attached shows' venues, approved or not) and a festival with no shows; an unfiltered listing shows every festival overlapping the window, with no New England filter, since a festival is added by an editor. A festival entry never counts toward the listing's "no matching events" state, which holds because a show-less festival is hidden when filtered.
5. **Festival page.** A view like `venue_page`: title, dates, description, shows grouped by day. The description is stored as rich text like `Event.description`; it's rendered through the same safe path used there.
6. **Editor override.** On the event admin, the festival field is a choice plus an explicit "not part of any festival" option; saving with either sets `festival_set_by="admin"`; clearing the choice resets it to automatic.
7. **Stored rows.** (An addition beyond the request, listed under Open Questions.) The event row and page get a small "part of <festival>" link. Rows are re-baked when the festival link changes, and when a festival's title or slug changes, for its attached events only.

## Risks / Trade-offs

- **Over- or under-matching** by name: mitigated by dates being required, the optional town, `--dry-run`, and the override. Acceptable per the thread (option c).
- **Re-baking many rows** when a big festival's title changes (hundreds of Porchfest shows): done in one pass inside the festival save, only for attached events.
- **Calendar entry placement** in the listing's data shape touches the shared index view and the day map reading the listing; the map reads event rows' `data-` attributes only, so the entry must not carry them.
- **Time zones:** dates are compared in New York time; tested at the day boundary.

## Open Questions

- **"Match its name or town".** The thread said shows attach when they match the festival's name or town. Taken here: the words (the title by default) are looked for in a show's title, artists text or venue town, so a festival named for a town matches shows in it, and the optional town field is an extra restriction for festivals whose name is common. A plain "name OR town" would attach every show in a town during the dates; say if that is wanted instead.
- **Additions the owner can strike.** `match_words` (needed when a festival's shows spell its name differently), the tie-break for several matching festivals (latest start, then lowest id, only so the result is predictable), matching on the artists text as well as the title, the `match_festivals` command (needed to apply a new festival to shows already imported), the "part of <festival>" link on event pages and rows (which forces re-rendering stored rows), and the sitemap and "past" marking. None was asked for in the issue. Without the row link, the event page link would remain as the minimum.
- Should the calendar entry also appear on the saved-shows and search pages? Assumed not.
- Should a festival hide or fold its own shows from the listing once there are very many (Porchfest can have hundreds)? Assumed no for now; the thread asked for one entry in addition, not instead.
- When a festival spans several towns, is a single town field enough? Assumed one town or none.
- Do festivals get calendar-feed (`.ics`) entries? Assumed not.

## Testing

All tests are Django `TestCase`s with no network. Festivals add no outside service. `fetch_events` scenarios use the existing mocked fetchers and recorded fixtures (`core/tests/fixtures/`), with Anthropic, Ticketmaster, Eventbrite, SeatGeek and venue websites mocked as the current import tests do. Dates use an injected current time as other view tests do.

## Sketches

Three static sketches of the calendar entry and the festival page (1440×900):

- [Option A: Plum banner and festival card](sketches/a.html). Thesis: the calendar entry is a full-width plum band, the site's navigation colour, so a festival reads as a divider in the day. The page is a filed index card under a plum name tab, like an act. Risk: plum means navigation and structure, so a banner may look like a month bar or a heading, and several festivals on one day stack into heavy bands.
- [Option B: Lavender span strip and night-by-night page](sketches/b.html). Thesis: the entry is a lavender strip with a small ruler of the days it covers, making the multi-day span visible at a glance. The page is a header, a jump row of nights and plum night headers. Risk: lavender means the strips a visitor acts on, so the entry may be mistaken for a filter, and the day ruler gets cramped for long festivals.
- [Option C: Quiet bold row and schedule table](sketches/c.html). Thesis: the entry is one cream, bold row with the date span in the time column, as dense as a show row. The page is a facts card with a day, time and act table for scanning hundreds of shows. Risk: the row is easy to skim past for a big event like Porchfest, and a table is a new pattern beside the site's ruled rows.
