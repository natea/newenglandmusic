Issue: [#159 Porchfest events should represented as multi-day festivals](https://github.com/natea/newenglandmusic/issues/159)

## Why

A festival like Porchfest is, on the site today, a pile of separate shows. There is no record of the festival itself: no title, no dates, no description, and no page a visitor can land on to see what it is. Issue 159 asks for a festival object with those three things. The thread settled the rest: visitors get a page per festival, the festival also appears as one multi-day entry in the main calendar, and shows are attached to a festival automatically with an editor able to correct it.

## What Changes

- **A festival record.** Editors add a festival in the admin with a title, a start date, an end date (a one-day festival has the same date twice) and a description. It gets a readable address made from its title, like venues do.
- **A festival page** at `/festivals/<slug>`: the title, the dates, the description, then the festival's shows night by night. Pages are indexable and listed in the sitemap.
- **One multi-day entry in the main calendar.** The home listing and the month archives show the festival once, as a banner-style entry linking to its page, on the first day it is on screen and marked as running through its end date. Its individual shows are still listed on their own days, as today.
- **Shows attach to festivals automatically.** A show with a start time attaches to a festival when its start falls within the festival's dates (New York time) and its title, artists or venue town matches the festival's match words (the festival title by default, plus an optional town). The match runs when an event is saved and when a festival's dates or match words change.
- **Editors can override.** An editor can set a festival on a show, or mark a show "not part of any festival", in the admin. An editor's choice is never changed by automatic matching.
- **Unchanged:** shows keep their own pages, rows and feeds; no event is hidden, merged or deleted, and no existing event field changes meaning.

## Capabilities

### New Capabilities
- `festivals`: the festival record, its page, its multi-day calendar entry, automatic matching of shows and the editor's override.

### Modified Capabilities
- `event-import`: (adds requirements only; no existing one changes) a newly fetched or re-fetched show goes through festival matching when it is saved, and a re-fetch never undoes an editor's override.

## Additions beyond the request

The issue and thread asked for the record, its page, the calendar entry, and automatic attachment with editor override. Match words, the several-festival tie-break, the "part of" link on rows, the `match_festivals` command, the sitemap and past marking are additions; the design lists them as open questions the owner can strike.

## Impact

- **Code:** a new `Festival` model and a nullable `Event.festival` link with a "set by" marker (a migration); a new `core/festivals.py` for the matching; a festival admin and a festival field on the event admin; a view and template for the page, a route in `core/urls.py`; the calendar view `core/views/index.py` and `core/templates/core/index.html` for the entry; `core/sitemap.py`; the event page and row templates for a small "part of <festival>" link.
- **Stored HTML:** event rows are stored rendered, so a row's "part of" link needs the row re-rendered when its festival changes. Saving a festival does not call `Venue.save()`-style bulk re-rendering; only the events whose attachment changed are re-rendered.
- **Data:** a migration adds a table and one nullable column. Existing events are untouched until a festival is created; matching a new festival over past and upcoming events is a command, run by hand with `--dry-run` first.
- **No new outside services.** Calendar feeds, ticketing and AI extraction are unchanged.
