## Purpose

What the site tells search engines and other crawlers: `robots.txt`, each page's canonical address, structured data and what it may contain, and the sitemap's shape, dates and range.

## ADDED Requirements

### Requirement: robots.txt names the sitemap and keeps crawlers out of private pages
`/robots.txt` SHALL answer 200 with plain text, without a redirect. It SHALL allow crawling for every user agent, except the admin, the email-digest pages, search results, internal APIs and the per-event calendar downloads. It SHALL name the sitemap's address on `SITE_URL`.

#### Scenario: Fetching robots.txt
- **WHEN** a crawler fetches `/robots.txt`
- **THEN** it gets 200, `text/plain`, a `Sitemap:` line with `https://stagehopper.app/sitemap.xml`, and `Disallow` lines for `/admin/`, `/digest`, `/search`, `/internal-api/`, `/event/*/ics` and `/event/*/gcal`

#### Scenario: Not redirected
- **WHEN** `/robots.txt` is fetched
- **THEN** it isn't redirected to `/robots.txt/`

### Requirement: Every public page has one canonical address
Every public page that may be indexed SHALL carry a `<link rel="canonical">`, and an `og:url` with the same value. The value SHALL be `SITE_URL` followed by the path the page is served at without a redirect, with no query string. Search results, the email-digest pages and the 404 page SHALL ask not to be indexed, and SHALL carry no canonical link.

#### Scenario: A filtered home page
- **WHEN** a visitor opens `/?state=vermont`, or `/` with a remembered state filter
- **THEN** the canonical link and `og:url` are `https://stagehopper.app/`

#### Scenario: An act page
- **WHEN** the page `/bands/belly` is fetched
- **THEN** its canonical link and `og:url` are `https://stagehopper.app/bands/belly`, with no trailing slash

#### Scenario: A month page
- **WHEN** `/2026-12/` is fetched
- **THEN** its canonical link is `https://stagehopper.app/2026-12/`

#### Scenario: Search results
- **WHEN** a search results page is fetched
- **THEN** it asks not to be indexed and has no canonical link

### Requirement: Pages describe their events and acts as structured data
Pages SHALL carry schema.org JSON-LD built from the same records they show:
- the home page: a `WebSite` with the site's name and address;
- a band page: a `MusicGroup`;
- an artist page: a `Person`;
- an event page: a `MusicEvent`;
- a venue page: a `MusicVenue`.

A band or artist page's JSON-LD SHALL include the act's name, page address, town and state, `sameAs` links, and up to 10 upcoming approved shows as `MusicEvent`s. A venue page's SHALL include the venue's name, address and page address, and up to 10 upcoming approved shows. Each `MusicEvent` SHALL carry:
- its start time with its UTC offset;
- its status, as cancelled when it's cancelled;
- its venue as a `MusicVenue`, with the venue's own address;
- its performers in billing order;
- a ticket offer when it has a ticket link.

#### Scenario: A band with an upcoming show
- **WHEN** the band "Belly" has an approved show at The Sinclair on Dec 5 at 8 pm
- **THEN** its page's JSON-LD is a `MusicGroup` named Belly, whose `event` lists a `MusicEvent` starting `2026-12-05T20:00:00-05:00` at a `MusicVenue` named The Sinclair

#### Scenario: A cancelled show
- **WHEN** one of the act's upcoming shows is cancelled
- **THEN** that `MusicEvent`'s `eventStatus` is `https://schema.org/EventCancelled`

#### Scenario: An artist
- **WHEN** the artist "Anjimile" from Boston, MA has a page
- **THEN** its JSON-LD is a `Person` with a `homeLocation` of Boston, MA

#### Scenario: An event page
- **WHEN** the page of Belly's Dec 5 show at The Sinclair, with Anjimile opening, is fetched
- **THEN** its JSON-LD is a `MusicEvent` with that start time, The Sinclair as a `MusicVenue`, and the performers Belly then Anjimile, each with its page address

#### Scenario: A venue page
- **WHEN** The Sinclair's venue page is fetched and it has three upcoming approved shows
- **THEN** its JSON-LD is a `MusicVenue` named The Sinclair with the sheet's address, listing the three shows

#### Scenario: The home page
- **WHEN** the home page is fetched
- **THEN** its JSON-LD is a `WebSite` named StageHopper with the address `https://stagehopper.app/`

### Requirement: Structured data carries only what the site may publish
JSON-LD SHALL take venue addresses only from the venue sheet, never from Google Places. It SHALL NOT include anything from Last.fm, Spotify or Apple Music, or any Wikipedia text. `sameAs` SHALL list only the act's website, MusicBrainz, Wikidata, Wikipedia, Bandcamp and Instagram links. A ticket offer SHALL never link to SeatGeek; a SeatGeek event's offer SHALL use the same ticket link the listing shows.

#### Scenario: A venue matched on Google Places
- **WHEN** a venue has a Google Places address and coordinates, and a different street address in the sheet
- **THEN** the JSON-LD carries the sheet's address and no coordinates

#### Scenario: An act matched on Spotify and Apple Music
- **WHEN** an act has Spotify, Apple Music and MusicBrainz links
- **THEN** its `sameAs` includes the MusicBrainz link and nothing from Spotify or Apple Music

#### Scenario: A SeatGeek event
- **WHEN** a show fetched from SeatGeek has the venue's Etix page as its ticket link
- **THEN** its offer's `url` is that Etix page, not SeatGeek

### Requirement: The sitemap is an index of dated, sorted sections
`/sitemap.xml` SHALL be a sitemap index of sections:
- pages: home, static pages, the band index;
- months: from the earliest month with an approved New England event up to 12 months ahead;
- acts: every live band and artist page, inactive ones included, with its last-modified date;
- events: the page of every upcoming approved New England event, with its last-modified date; a past event's page asks not to be indexed (`event-pages`), so it isn't listed;
- venues: the page of every active New England venue, with its last-modified date.

Each section SHALL list its addresses on `SITE_URL`, sorted, with at most 50,000 entries a file. Later changes MAY add sections, such as area pages.

#### Scenario: The index
- **WHEN** `/sitemap.xml` is fetched
- **THEN** it's a sitemap index naming the pages, months, acts, events and venues sections, each on `https://stagehopper.app`

#### Scenario: Far-off months left out
- **WHEN** an approved event is dated 2030-10, more than 12 months ahead
- **THEN** the months section doesn't list `/2030-10/`

#### Scenario: Events in range
- **WHEN** one approved show is next week, one was last week, and one is unapproved
- **THEN** the events section lists only next week's show

#### Scenario: Venues listed
- **WHEN** one venue is active in Vermont, one is inactive, and one is in New York
- **THEN** the venues section lists only the Vermont venue

#### Scenario: An edited band
- **WHEN** an editor changes a band's town in the admin
- **THEN** the band's sitemap entry's `lastmod` is that day

#### Scenario: A stable order
- **WHEN** the acts section is fetched twice
- **THEN** its entries are in the same, sorted order both times

### Requirement: The default description names New England only
A page with no description of its own SHALL use the default description, which SHALL name New England and its six states, and SHALL NOT say "Northeast".

#### Scenario: The home page's description
- **WHEN** the home page is fetched
- **THEN** its description names New England and doesn't say "Northeast"
