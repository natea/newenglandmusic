# Design

## Context

- **The submission form:** `UserSubmittedEventForm` (`core/views/event_submission.py`) is a `ModelForm` on `Event`. Its venue field uses the `dal` autocomplete over active venues, and its `clean()` raises "event must contain some venue information" when no venue is picked. `save()` marks the event unapproved and user-submitted. When `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION` is on, it emails `CONTACT_EMAIL` through `aws_mail_sender` (SES).
- **Approval:** events are approved in `EventAdmin` by the `mark_as_approved` action, which uses `queryset.update(is_approved=True)`, or by the change form's checkbox, through `save_model`.
- **Venues:** they come only from `sync_venues_from_gsheets`, keyed by the sheet's `Venue_ID`. `Venue.state` is a two-letter code, and venues span 12 of them today (MA, NH, ME, NY, CT, VT, RI, PA, NJ, DC, MD and DE).
- **URLs:** a static-page catch-all ends `nycnoise/urls.py`, so new routes go in `core/urls.py`.
- **Links:** link fields save scheme-less input with `https://`, using `assume_scheme` and a text input (from `upgrade-django-5-2`).

## Goals / Non-Goals

**Goals:**
- No submission is lost because its venue isn't listed.
- The sheet stays the only source of venues. The site only collects and tracks suggestions.
- Reviewing a suggestion and its events takes a few clicks.

**Non-Goals:**
- Writing to the Google Sheet from the site. Admins add the row by hand, as now. A helper that formats a suggestion as a sheet row could come later.
- Venue details beyond what the suggestion page asks for: type, size, genres and the rest are filled in on the sheet.
- CAPTCHA or rate limiting. The hidden field stops simple bots, and anything more can follow if spam gets through.
- Fuzzy duplicate detection, such as "Paradise" vs "Paradise Rock Club". The exact-name check catches the obvious repeats, and admins catch the rest.

## Decisions

**A `VenueSuggestion` model, not a venue flagged as pending.**
- **Fields:** name, town, state, website, notes, submitter email, a status (`pending`, `added` or `rejected`), a nullable `venue` link, and `created_at` / `updated_at`.
- **Why not a pending `Venue`:** a "pending" `Venue` would put rows with no sheet ID into the model the sheet sync owns. It would also leak into the autocomplete, the filters and the Places lookup.
- **The event side:** `Event.venue_suggestion` is a nullable FK (`SET_NULL`), so one suggestion can carry several submitted events.

**One form class for the suggestion fields, reused by both entry points.** A plain `VenueSuggestionForm` holds the name, town, state and website fields, the state choices, the duplicate check and the hidden field.
- **On its own:** the `/suggest-venue` page uses it directly.
- **Inside the event form:** `UserSubmittedEventForm` gains an `unlisted_venue` checkbox and prefixed copies of the same fields.
  - Its `clean()` requires exactly one of a picked venue or a complete unlisted venue, and runs the shared duplicate check.
  - Its `save()` creates the suggestion and links the event in one transaction.
- **State choices** are the distinct `Venue.state` values, read when the form is built, so they follow the sheet.

**The duplicate check is an exact match, done in the database.** It looks for an active venue (anything but `is_active=False`) with `name__iexact`, `city_town__iexact` and the same `state`, after trimming. The error names the venue and says to pick it from the venue list.

**The hidden field is a decoy, not a CAPTCHA.** It's a text field named `website_url`, hidden with CSS and `autocomplete="off"` / `tabindex="-1"`, plus an `aria-hidden` label telling people to leave it blank. When it's filled, the view skips saving and emailing and returns the normal success redirect, so bots get no signal.

**Linking happens on the suggestion's admin page.** `VenueSuggestionAdmin` has a `venue` autocomplete field. Saving with a venue chosen sets the status to `added` and runs `Event.all_objects.filter(venue_suggestion=s, venue__isnull=True)`. Each of those events is saved with that venue through `save()`, not `update()`, so its stored HTML is rendered with the venue. A "reject" action sets the status to `rejected`. An inline lists the suggestion's events, linking to their admin pages. The list filters by status and puts pending first.

**The approval block lives in both approval paths.**
- **Bulk action:** `mark_as_approved` excludes `venue__isnull=True, venue_suggestion__isnull=False` and reports the skipped count with `message_user`.
- **Event page:** the event admin form's `clean()` raises a validation error when `is_approved` is ticked on such an event.
- **Review list:** a "waiting for venue" column and a list filter show which events these are.

**Emails reuse the existing path.** The event email gains the unlisted venue's name, town and state. A suggestion from `/suggest-venue` sends its own short email. Both are behind the existing setting, so nothing is sent by default.

**Testing and external services.** The only external service is SES, through `aws_mail_sender.send_email`, which the tests replace with a mock to check it's called, or not called. `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION` is switched on with `override_settings`. Everything else uses the Django test client and the test database. The admin tests call `EventAdmin` and `VenueSuggestionAdmin` with a `RequestFactory` superuser, as `test_venue_admin` does. Nothing calls the sheet, Places, Ticketmaster or Anthropic, and the suite still runs with outbound network blocked.

## Risks / Trade-offs

- [Spam suggestions pile up.] → The hidden field drops simple bots, and suggestions never reach the public site. If spam gets through, add rate limiting or a CAPTCHA as a follow-up.
- [An admin forgets to link a suggestion after syncing the venue.] → Pending suggestions sort first and their events are visibly waiting. A link to the waiting-for-venue filter on the review list keeps them in view.
- [A linked venue later turns out wrong.] → The link only sets `venue` on events that had none, and admins can edit those events as usual.
- [Users submit the same unlisted venue twice before it's added.] → Each creates its own suggestion. Admins link both to the same venue, and the admin list shows names together.

## Migration Plan

One additive migration: the `VenueSuggestion` table and the `Event.venue_suggestion` column. Release through `main` as usual, with Render's build running `migrate`. Then add the suggestion page to the menu (Menu items in the admin), on the live site as well as locally.

**Rollback:** revert the release. The table and column can stay, or be dropped by a later migration.
