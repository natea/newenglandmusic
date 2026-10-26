# Proposal

## Why

Nobody outside the team can add a venue. The event submission form only accepts a venue already on the site, and it rejects an event with no venue. So a show at an unlisted venue can't be submitted at all, and there's nowhere to tell us about a venue we've missed. Venues have to stay in the Google Sheet, which is the master list, so the site should collect suggestions for review rather than create venues itself.

## What Changes

- **A "suggest a venue" page** at `/suggest-venue`. It asks for the venue's name, town, state and website, with optional notes and the visitor's email, and saves the suggestion for review.
- **The event submission form gets a "my venue isn't listed" option.** Instead of picking a venue, the submitter can enter its name, town and state. The event is saved unapproved and linked to a new venue suggestion, so both arrive together.
- **Duplicate check:** a suggestion that names an active venue already listed in the same town is refused, with a message saying how to pick that venue instead.
- **Review in the admin:**
  - Suggestions have their own admin list (pending, added or rejected) showing their waiting events.
  - Once an accepted venue has been added to the sheet and synced, an admin links the suggestion to it. That sets the venue on the suggestion's waiting events, which then go through the usual event review.
  - A suggestion can also be linked to a venue that already existed, or rejected.
- **An event waiting for its venue can't be approved**, either from the review list's bulk action or from the event's own page. The review list shows which events are waiting and can filter to them.
- **Spam protection:** both public forms get a hidden field that people never fill in. Submissions that fill it are dropped without saving.
- **Notifications:** when submission emails are turned on, a new suggestion is emailed like a new event, and an event email includes any venue it suggests.
- Venues are still created only by `sync_venues_from_gsheets`. Nothing here creates or edits a `Venue`.

## Capabilities

### New Capabilities

- `venue-suggestions`: suggesting a venue, from its own page or from the event form, and reviewing suggestions in the admin up to the point where their events can be approved.

### Modified Capabilities

None. The event submission form has no spec yet, and this change's spec covers the parts of it that it changes.

## Impact

- **Models:**
  - a new `VenueSuggestion`, with name, town, state, website, notes, submitter email, status, linked venue and timestamps
  - `Event.venue_suggestion`, a nullable link to it
  - one migration
- **Views and templates:**
  - a new suggestion page and its route, ahead of the static-page catch-all
  - `UserSubmittedEventForm` and its template gain the unlisted-venue fields and the hidden field
- **Admin:**
  - a `VenueSuggestionAdmin`
  - in `EventAdmin`: a "waiting for a venue" column and filter, and a block on approving those events in `mark_as_approved` and `save_model`
- **Email:** the existing `aws_mail_sender` path, behind `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION`.
- **The sheet:** no change to `sync_venues_from_gsheets`. Admins add accepted venues to the sheet by hand, as now.
