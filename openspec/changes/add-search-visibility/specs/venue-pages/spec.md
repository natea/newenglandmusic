## MODIFIED Requirements

### Requirement: Venue pages are reachable and can be found
The event page SHALL link its venue's name to the venue page, and the venue's admin page SHALL offer "View on site". The venue page SHALL be open to search engines, with a canonical link to itself. The page SHALL describe the venue as a `MusicVenue` in structured data, with its upcoming shows, and the sitemap SHALL list it (`search-visibility`).

#### Scenario: From an event page
- **WHEN** a visitor opens an event at O'Brien's
- **THEN** "O'Brien's" links to `/venues/obriens`

#### Scenario: Can be indexed
- **WHEN** a search engine fetches a venue page
- **THEN** the page carries no `noindex`, and its canonical link is its own address

#### Scenario: Structured data and the sitemap
- **WHEN** an active Vermont venue has a page
- **THEN** the page carries a `MusicVenue` for it, and the sitemap's venues section lists its address
