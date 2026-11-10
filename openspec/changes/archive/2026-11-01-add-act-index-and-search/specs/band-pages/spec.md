## ADDED Requirements

### Requirement: Act pages are found by search engines
Every live band and artist page SHALL be open to search engines, whether or not the act has an upcoming show, and the sitemap SHALL list every live band and artist page and the index at `/bands`. An act held for review SHALL NOT be in the sitemap.

#### Scenario: No upcoming show
- **WHEN** a search engine fetches the page of a band with no upcoming shows
- **THEN** the page doesn't ask not to be indexed

#### Scenario: The sitemap
- **WHEN** the sitemap is fetched
- **THEN** it lists `/bands` and the page of every live band and artist, with or without shows, and no held act
