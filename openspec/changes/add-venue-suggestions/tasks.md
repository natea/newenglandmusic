# Tasks

## 1. Model

- [ ] 1.1 Add `VenueSuggestion` (name, town, state, website, notes, submitter email, status, venue, timestamps) and the nullable `Event.venue_suggestion` FK, in one migration. Verify: `makemigrations --check` is clean and `migrate` applies locally.

## 2. Suggestion page

- [ ] 2.1 Add `VenueSuggestionForm`, with state choices from the venues' states, `https://` for scheme-less websites, and the exact-match duplicate check. Add the `/suggest-venue` page and template with a thank-you message, routed ahead of the static-page catch-all. Verify: tests for the "Suggestion saved", "Missing town", "Venue already listed" and "Same name in another town" scenarios.
- [ ] 2.2 Add the hidden decoy field to the suggestion page: when it's filled, the page answers as if it succeeded but saves nothing and sends no email. Verify: a test for the "Bot fills the hidden field" scenario.

## 3. Event form

- [ ] 3.1 Add the "my venue isn't listed" choice and unlisted-venue fields to `UserSubmittedEventForm`. Require exactly one of a picked or an unlisted venue, run the duplicate check, and save the suggestion and the linked event together. Add the decoy field to this form too. Verify: tests for the "Event at an unlisted venue", "Neither venue nor unlisted venue" and "Unlisted venue that is listed" scenarios, and for the decoy field on this form. The existing submission tests still pass.
- [ ] 3.2 Show and hide the unlisted-venue fields with a little JavaScript, keeping the form usable without it. Verify: at localhost:8001/submit-event, both ways of giving a venue work with JavaScript on and off.

## 4. Admin

- [ ] 4.1 Add `VenueSuggestionAdmin`: a status filter with pending first, an inline of waiting events, a venue autocomplete that links the suggestion and sets that venue on its venue-less events through `save()`, and a reject action. Verify: tests for the "Pending suggestions first", "Link after the venue is added to the sheet" and "Reject a suggestion" scenarios.
- [ ] 4.2 Block approving events waiting for a venue, in `mark_as_approved` (skip and report) and on the event admin form (validation error). Add a "waiting for venue" column and filter to the review list. Verify: tests for the "Bulk approve skips a waiting event" and "Approving from the event page" scenarios.

## 5. Email

- [ ] 5.1 Email new suggestions, and include the unlisted venue in event emails, behind the existing setting, with `aws_mail_sender` mocked in tests. Verify: a test for the "Emails on" scenario, and a test that nothing is sent when emails are off.

## 6. Release

- [ ] 6.1 Run the full suite with outbound network blocked, then walk through it on the local dev server: suggest a venue, submit an event at an unlisted venue, link the suggestion to an existing venue in the admin, and approve the event. Verify: every test passes, and the walk-through works end to end.
- [ ] 6.2 With the user's go-ahead, push to `main`, then add "suggest a venue" to the menu on the live site. Verify: `/suggest-venue` loads on the live site, and a test suggestion appears in the live admin (then delete it).

## Workflow follow-up

- Archive with `/opsx:archive add-venue-suggestions` once every task is checked.
