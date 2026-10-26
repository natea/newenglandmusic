# Spec Delta

## Purpose

A public page for each region, state and metro area the filters offer, at a stable address, listing that area's upcoming shows.

## ADDED Requirements

### Requirement: Each offered area has a page

Each region, state and metro area offered in the listing filters SHALL have a page at `/region/<slug>/`, `/state/<slug>/` or `/metro/<slug>/`. The page SHALL list the same upcoming events as the home page with that one filter applied. It SHALL have a title and heading naming the area, and SHALL link to that area's month listings. A slug that isn't an offered area of that kind SHALL return 404.

#### Scenario: State page

- **WHEN** a visitor opens `/state/vermont/`
- **THEN** the page returns 200, its heading names Vermont, and it lists only events at Vermont venues

#### Scenario: Metro page

- **WHEN** a visitor opens `/metro/ny-hudson-valley/`
- **THEN** only events at venues in the Hudson Valley counties are listed

#### Scenario: Unknown area

- **WHEN** a visitor opens `/state/atlantis/`
- **THEN** the response is 404

#### Scenario: Area of the wrong kind

- **WHEN** a visitor opens `/metro/vermont/` and no metro has the slug `vermont`
- **THEN** the response is 404

### Requirement: Area pages ignore the remembered filter

An area page SHALL NOT read, set or clear the remembered-filter cookie, and SHALL NOT redirect.

#### Scenario: Visitor with a remembered filter

- **WHEN** a visitor whose cookie holds `state=maine` opens `/state/vermont/`
- **THEN** Vermont events are listed, the request isn't redirected, and the cookie still holds `state=maine`
