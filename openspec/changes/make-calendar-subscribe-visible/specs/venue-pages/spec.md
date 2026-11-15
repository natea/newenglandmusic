## ADDED Requirements

### Requirement: A venue's page offers calendar subscription
A venue's page SHALL show the same visible "Subscribe" button as the listing, near the top of the page. It SHALL subscribe to the calendar feed of the state the venue is in, and its label SHALL name that state (for example "Subscribe: Massachusetts"). When the venue has no state, or its state is not an offered area, it SHALL subscribe to the feed of all areas. It SHALL work without JavaScript.

#### Scenario: Venue in a state
- **WHEN** a visitor opens the page of a Massachusetts venue
- **THEN** the Subscribe button's links point at `/calendar.ics?state=massachusetts`, and the label names Massachusetts

#### Scenario: Venue with no state
- **WHEN** a visitor opens the page of a venue with no state
- **THEN** the Subscribe button's links point at `/calendar.ics`, with no parameters

#### Scenario: Venue in a state that is not an offered area
- **WHEN** a visitor opens the page of a venue whose state is not an offered area
- **THEN** the Subscribe button's links point at `/calendar.ics`, with no parameters
