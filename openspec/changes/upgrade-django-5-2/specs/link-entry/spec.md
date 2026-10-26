# Spec Delta

## Purpose

How web addresses that people type into the site's forms and the admin are completed and stored, so links work when someone leaves off the scheme.

## ADDED Requirements

### Requirement: Links typed without a scheme use https

When a person enters a web address without a scheme (`http://` or `https://`) in a link field, the system SHALL store it with `https://` added. This applies to the public event submission form (the event link and the ticket link) and to every link field in the event and venue admin forms. An address entered with an explicit scheme SHALL be stored with that scheme unchanged.

#### Scenario: Event submitted with scheme-less links

- **WHEN** someone submits an event with the link `example.com/show` and the ticket link `tickets.example.com/123`
- **THEN** the event's links are `https://example.com/show` and `https://tickets.example.com/123`

#### Scenario: Venue website entered in the admin without a scheme

- **WHEN** an admin saves a venue whose website is entered as `example.com`
- **THEN** the venue's website is stored as `https://example.com`

#### Scenario: Explicit http is kept

- **WHEN** someone enters a link that starts with `http://`, on the submission form or in the admin
- **THEN** the link is stored with `http://`, unchanged
