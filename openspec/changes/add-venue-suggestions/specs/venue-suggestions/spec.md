# Spec Delta

## Purpose

Let visitors tell us about venues the site doesn't list, from their own page or while submitting an event, and let admins review those suggestions into the Google Sheet without the site ever creating venues itself.

## ADDED Requirements

### Requirement: Visitors can suggest a venue

The site SHALL have a public page at `/suggest-venue` that asks for a venue's name, town and state, which are required, and its website, notes and the visitor's email, which are optional. The state SHALL be chosen from the states the site's venues are in. A valid submission SHALL be saved as a pending suggestion and SHALL NOT create a venue. The visitor SHALL then see a thank-you message.

#### Scenario: Suggestion saved

- **WHEN** a visitor submits "The Lilypad", "Cambridge", "MA" and `lilypadinman.com`
- **THEN** a pending suggestion is saved with those details, the website is stored as `https://lilypadinman.com`, no venue is created, and the visitor sees a thank-you message

#### Scenario: Missing town

- **WHEN** a visitor submits a venue name and state but no town
- **THEN** the form is shown again with an error on the town, and nothing is saved

### Requirement: Suggestions of listed venues are refused

A suggestion whose name matches an active venue in the same town and state, ignoring case and surrounding spaces, SHALL be refused. The visitor SHALL be told the venue is already listed, and nothing SHALL be saved.

#### Scenario: Venue already listed

- **WHEN** a visitor suggests "paradise rock club" in Boston, MA, and an active venue "Paradise Rock Club" in Boston, MA exists
- **THEN** the form says the venue is already listed, and no suggestion is saved

#### Scenario: Same name in another town

- **WHEN** a visitor suggests "The Middle East" in Portland, ME, and the only venue with that name is in Cambridge, MA
- **THEN** the suggestion is saved

### Requirement: An event can be submitted for an unlisted venue

The event submission form SHALL offer a "my venue isn't listed" choice in place of picking a venue. When it's chosen, the venue's name, town and state SHALL be required, and the submission SHALL save a pending venue suggestion and an unapproved event linked to it, with no venue set. A submission SHALL have either a picked venue or an unlisted venue, not both and not neither. The duplicate check SHALL apply to the unlisted venue too.

#### Scenario: Event at an unlisted venue

- **WHEN** someone submits an event and enters "The Lilypad", "Cambridge", "MA" as an unlisted venue
- **THEN** an unapproved event is saved with no venue, linked to a new pending suggestion for The Lilypad

#### Scenario: Neither venue nor unlisted venue

- **WHEN** someone submits an event without picking a venue or entering an unlisted one
- **THEN** the form shows an error, and nothing is saved

#### Scenario: Unlisted venue that is listed

- **WHEN** someone enters "Paradise Rock Club", "Boston", "MA" as an unlisted venue, and that venue is listed and active
- **THEN** the form says to pick it from the list, and nothing is saved

### Requirement: Automated spam is dropped

The suggestion page and the event submission form SHALL each include a field hidden from people. A submission that fills it in SHALL be answered as if it succeeded, but SHALL save nothing and send no email.

#### Scenario: Bot fills the hidden field

- **WHEN** a submission to `/suggest-venue` fills in the hidden field
- **THEN** the response looks like a success, and no suggestion is saved

### Requirement: Admins can review suggestions

The admin SHALL list venue suggestions with their status (pending, added or rejected), filterable by status, with pending ones first. Each suggestion SHALL show its waiting events. The admin SHALL NOT create or edit a venue from a suggestion.

#### Scenario: Pending suggestions first

- **WHEN** an admin opens the suggestions list, and there are pending, added and rejected suggestions
- **THEN** the pending ones are listed first, and each shows how many events are waiting on it

### Requirement: Admins can link a suggestion to a venue

An admin SHALL be able to link a suggestion to an existing venue, whether it was just added to the sheet and synced or was already listed. Linking SHALL set the suggestion's status to added, and SHALL set that venue on each of its events that has no venue yet. Those events SHALL stay unapproved.

#### Scenario: Link after the venue is added to the sheet

- **WHEN** a pending suggestion has two waiting events, the venue has been added to the sheet and synced, and an admin links the suggestion to that venue
- **THEN** the suggestion is marked added, and both events have that venue and are still unapproved

### Requirement: Admins can reject a suggestion

An admin SHALL be able to reject a suggestion. Rejecting SHALL set its status to rejected, and SHALL leave its events unapproved and without a venue.

#### Scenario: Reject a suggestion

- **WHEN** an admin rejects a pending suggestion
- **THEN** it is marked rejected, and no venue is created or changed

### Requirement: Events waiting for a venue can't be approved

An event linked to a suggestion and with no venue set SHALL NOT be approved, either by the review list's bulk approve action or from the event's own admin page. The bulk action SHALL approve the other selected events and report how many it skipped. The event's own page SHALL show an error. The review list SHALL show which events are waiting for a venue, and SHALL be filterable to them.

#### Scenario: Bulk approve skips a waiting event

- **WHEN** an admin bulk-approves three events, one of which is waiting for a venue
- **THEN** two events are approved, the waiting one isn't, and the admin is told one was skipped

#### Scenario: Approving from the event page

- **WHEN** an admin ticks "is approved" on an event that is waiting for a venue and saves
- **THEN** the page shows an error and the event stays unapproved

### Requirement: New suggestions are emailed when submission emails are on

When submission emails are turned on, a new suggestion from the suggestion page SHALL be emailed to the contact address, and an event email SHALL include the unlisted venue's name, town and state. When they're off, no email SHALL be sent.

#### Scenario: Emails on

- **WHEN** submission emails are on and a visitor suggests a venue
- **THEN** one email is sent to the contact address with the venue's name, town and state
