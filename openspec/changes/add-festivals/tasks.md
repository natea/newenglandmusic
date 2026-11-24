Issue: [#159 Porchfest events should represented as multi-day festivals](https://github.com/natea/newenglandmusic/issues/159)

## 1. The record

- [ ] 1.1 Add `Festival`, the `Event.festival` and `festival_set_by` fields and a migration; make slugs unique and validate end date not before start. Add a pre-delete step that returns the festival's shows to automatic and re-bakes their rows. Test every "editors keep festivals" scenario: create, one-day, end before start, same title twice, deleting a festival, deleting a festival with an editor-attached show.
- [ ] 1.2 Register the festival in the admin (title, dates, description, match words, town) and add the festival choice, "not part of any festival" and a filter on the event admin. Test the override and filter scenarios.

## 2. Matching

- [ ] 2.1 Write `core/festivals.py` (`festival_for`, `rematch`, `rematch_festival`) comparing dates in New York time. Use `select_related("venue")` when matching in bulk. Test the matching scenarios: title in dates, wrong dates, town restriction, late-night last day, several festivals, same start day tie, no start time, dates change, show moves, unapproved show, own match words, nothing matches.
- [ ] 2.2 Call it from `Event.save()` (computing the festival before `super().save()`) and the festival save, never overriding an editor's choice, re-baking only changed rows. Test that an event adopted by `fetch_events`'s `existing_copy` path keeps its editor choice. Test that the editor's choice survives saves, festival edits and a `fetch_events` re-fetch, and that a new fetched show is matched (mock the fetchers as the existing import tests do).
- [ ] 2.3 Add `match_festivals` as a `RecordedCommand` with `--festival` and `--dry-run`. Test dry run and a real run, including the recorded job run.

## 3. Pages and calendar

- [ ] 3.1 Add the festival page view, template, route, sitemap entry and past marking. Test content, unapproved shows, no shows, unknown slug, past festival, indexability and sitemap.
- [ ] 3.2 Add the multi-day entry to the home listing and month archives, with the area filter rule. Test first-day placement, already running, shows keeping their days, the month archive, the area filter (including a festival with no shows and one with only unapproved shows in the area) and outside-window cases, and check the day map ignores the entry.
- [ ] 3.3 Add the "part of <festival>" link to the event page and row, re-baking on change. Test the link, the change and the no-festival case.

## 4. Finish

- [ ] 4.1 Update `PRODUCTION.md` and `AGENTS.md` with the new command, and run the whole suite with outbound network blocked.
