# Spec Delta

## Purpose

A public page for each approved event at its existing share link, instead of a redirect to the month page.

## ADDED Requirements

### Requirement: Each approved event has a page

`/event/<id>` SHALL be a page for the approved event with that ID. It SHALL show the event's title and artists, date and start time (or "time TBA"), venue, with a link to the venue's page, price, age policy and description. It SHALL also show the event's link, ticket link and calendar links where they exist, and a link to the event in its month's listing. An event that is unapproved or doesn't exist SHALL return 404.

#### Scenario: Approved event

- **WHEN** a visitor opens `/event/<id>` for an approved event at an active venue
- **THEN** the page returns 200 and shows the event's title, start time and venue, with links to the venue's page, the tickets, and the event in its month's listing

#### Scenario: Unapproved event

- **WHEN** a visitor opens `/event/<id>` for an event awaiting review
- **THEN** the response is 404

#### Scenario: Past or cancelled event

- **WHEN** a visitor opens the page of an event that has already happened, or one marked cancelled
- **THEN** the page returns 200 and says the event is past, or cancelled

### Requirement: Share links keep working

Share links SHALL keep the `/event/<id>` address, and SHALL keep the title, description and image tags that link previews read. A request without a User-Agent header SHALL get the page, not an error.

#### Scenario: Link preview

- **WHEN** a link preview service fetches `/event/<id>` for an approved event
- **THEN** the page has the event's title in its `og:title` tag and the page's own address in its `og:url` tag

#### Scenario: No User-Agent

- **WHEN** a client with no User-Agent header opens `/event/<id>` for an approved event
- **THEN** the response is 200
