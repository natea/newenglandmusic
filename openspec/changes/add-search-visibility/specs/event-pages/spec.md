## MODIFIED Requirements

### Requirement: The page shares well and can be found
The page SHALL have a title and description naming the event's acts, date and venue, and SHALL keep the preview metadata that shared links already show. An upcoming event's page SHALL be open to search engines, with a canonical link to itself. A past event's page SHALL ask search engines not to index it. The page SHALL describe the event as a `MusicEvent` in structured data, and the sitemap SHALL list it while it is upcoming (`search-visibility`).

#### Scenario: Share preview
- **WHEN** a link to an event page is shared
- **THEN** its preview names the date, venue and acts, as the old redirect page's did

#### Scenario: An upcoming event can be indexed
- **WHEN** a search engine fetches an upcoming event's page
- **THEN** the page carries no `noindex`, and its canonical link is its own address

#### Scenario: A past event isn't indexed
- **WHEN** a search engine fetches the page of an event that has passed
- **THEN** the page asks not to be indexed

#### Scenario: Structured data and the sitemap
- **WHEN** an approved show next week has a page
- **THEN** the page carries a `MusicEvent` for it, and the sitemap's events section lists its address
