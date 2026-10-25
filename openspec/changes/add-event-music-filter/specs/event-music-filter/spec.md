# Spec Delta

## Purpose

Labels each imported event with what kind of event it is, so the calendar's review queue shows performing music acts and keeps trivia, comedy, classes and other non-music events out of the way without losing them.

## ADDED Requirements

### Requirement: Imported events are labelled by kind
Each imported event SHALL be labelled `live_music`, `dj_dance`, `open_mic`, `karaoke`, `comedy` or `other`. `live_music`, `dj_dance` and `open_mic` SHALL count as music; the rest SHALL NOT. A themed party SHALL be labelled music only when a band, solo artist or DJ is billed.

#### Scenario: Tribute act on a holiday
- **WHEN** an event is titled "A Very Jerry Halloween with Rose Alley (Jerry Garcia Band Tribute)"
- **THEN** it is labelled `live_music`

#### Scenario: Party with nobody billed
- **WHEN** an event is titled "Halloween Costume Party" and lists no performers
- **THEN** it is labelled `other`

#### Scenario: Non-music nights
- **WHEN** events are titled "Trivia Night", "Nerd Night", "Clown Class", "Print Club" or "Sunday Night Karaoke"
- **THEN** none of them is labelled music

#### Scenario: DJ night and open mic
- **WHEN** events are titled "80s Dance Party with DJ Shakes" and "Tuesday Songwriter Open Mic"
- **THEN** they are labelled `dj_dance` and `open_mic`, which count as music

### Requirement: Labelling happens at import and in batches
`fetch_events` SHALL label events before saving them: AI-extracted events through their extraction, all other events in batches of at most 50 per request. Events already labelled SHALL NOT be labelled again.

#### Scenario: Re-import
- **WHEN** an event that already has a kind is imported again
- **THEN** no labelling request is made for it and its kind is unchanged

#### Scenario: Batching
- **WHEN** an import finds 120 unlabelled events from feeds and ticketing pages
- **THEN** they are labelled in 3 requests

### Requirement: An admin's label wins
An admin SHALL be able to change an event's kind. A kind set by an admin SHALL NOT be changed by later imports or by the `classify_events` command.

#### Scenario: Relabelled show
- **WHEN** an admin relabels an event from `other` to `live_music` and the import runs again
- **THEN** the event stays `live_music`

### Requirement: Non-music events are kept but hidden from review
Events labelled non-music SHALL be saved, unapproved, and SHALL be left out of the admin event list by default. The list SHALL offer a filter for kind, including non-music and unlabelled events. Labelling SHALL NOT change any event's approval.

#### Scenario: Default review list
- **WHEN** an admin opens the event list without choosing a kind
- **THEN** it shows music and unlabelled events, and no comedy, karaoke or other events

#### Scenario: Previously approved event
- **WHEN** an approved event is labelled `comedy`
- **THEN** it stays approved and stays on the site

### Requirement: Existing events can be labelled in a backfill
The `classify_events` command SHALL label existing upcoming imported events that have no kind. With `--dry-run` it SHALL report the kinds it would set, and list the events it would hide, without saving.

#### Scenario: Dry run of the backfill
- **WHEN** `classify_events --dry-run` runs
- **THEN** it reports counts per kind and lists events that would be hidden, and no event changes

### Requirement: Labelling degrades safely
Without `ANTHROPIC_API_KEY`, or when a labelling request fails, the events involved SHALL be saved unlabelled, SHALL remain in the default review list, and the failure SHALL be reported. A label outside the allowed kinds SHALL be treated as unlabelled.

#### Scenario: No API key
- **WHEN** `fetch_events` runs without `ANTHROPIC_API_KEY`
- **THEN** events are saved unlabelled and appear in the default review list

#### Scenario: Failed batch
- **WHEN** a labelling request fails
- **THEN** that batch's events are saved unlabelled, the failure is reported, and other batches are still labelled
