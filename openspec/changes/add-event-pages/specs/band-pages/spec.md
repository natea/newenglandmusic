## MODIFIED Requirements

### Requirement: Events link to their acts
Each performer of an event SHALL be reachable from the event: on the event's own page (`event-pages`), the headliner and each opener that is a performer SHALL link to that performer's band or artist page, including a performer's name that starts a longer title ("Built to Spill Fall 2026 Tour"). Names that aren't performers, and a presenter's prefix ("AS220 Presents:"), SHALL stay plain text. In calendar listings, act names SHALL NOT be links: the listing's one link is its headline, to the event's page (`event-listing`), and the listing SHALL carry no "info" link. The band page's show rows SHALL link to the event's page.

#### Scenario: A linked performer
- **WHEN** an event's Artists are "Pixies, Dana and Alden" and Pixies is a performer
- **THEN** on the event's page "Pixies" links to `/bands/pixies` and "Dana and Alden" stays plain

#### Scenario: The headliner in the title
- **WHEN** an event titled "Axe Collector" has the Artists "Phantom Rider, Zipper, Anthropocene", and Axe Collector, Phantom Rider and Zipper are performers
- **THEN** on the event's page all three names link to their pages and Anthropocene stays plain; in the listing none of the names is a link, and the headline links to the event's page

#### Scenario: No performers
- **WHEN** an event has no performers
- **THEN** its listing's headline links to the event's page, and the page shows its names as plain text
