# Spec Delta

## Purpose

What the sitemap and robots.txt tell search engines: which pages exist, in what order, when they last changed, and whether the site may be indexed yet.

## ADDED Requirements

### Requirement: The sitemap lists every public page

`/sitemap.xml` SHALL list, at the site's own address (`SITE_URL`):
- the home page and the published static pages;
- the month archive pages that have approved events;
- each offered area's page;
- each active venue's page;
- each upcoming approved event's page.

It SHALL NOT list unapproved events, past events, inactive venues or areas that aren't offered.

#### Scenario: All page kinds listed

- **WHEN** the site has an active venue with an upcoming approved event, and Vermont is an offered state
- **THEN** the sitemap lists the home page, that event's month page, `/state/vermont/`, the venue's page and the event's page, each starting with `SITE_URL`

#### Scenario: Hidden pages left out

- **WHEN** the site has an unapproved event, a past event and an inactive venue
- **THEN** none of their pages are in the sitemap

### Requirement: Sitemap entries are in a stable order

Entries SHALL be listed in the same order on every request: the home page and static pages, then the months in date order, then areas, venues and events, each sorted by address.

#### Scenario: Months in order

- **WHEN** the sitemap is fetched twice
- **THEN** both responses list the same entries in the same order, with the month pages in date order

### Requirement: Entries carry a last-modified date where known

An event page's entry SHALL carry the date the event last changed. A venue, area or month page's entry SHALL carry the latest change among the events it lists, or the venue's own last change if later. Pages with nothing to date SHALL have no last-modified date.

#### Scenario: Edited event

- **WHEN** an admin edits an upcoming event
- **THEN** the event page's last-modified date in the sitemap is the date of that edit

### Requirement: Search engines index the site only once allowed

`/robots.txt` SHALL name the sitemap's address. Until search indexing is turned on in the site's settings, `/robots.txt` SHALL disallow all crawling and every page SHALL tell search engines not to index it. Once indexing is turned on, `/robots.txt` SHALL allow crawling of the public pages and disallow `/admin/`, and pages SHALL no longer carry the no-index instruction.

#### Scenario: Before launch

- **WHEN** search indexing isn't turned on and a crawler fetches `/robots.txt`
- **THEN** it disallows all crawling and names the sitemap, and the home page carries a no-index instruction

#### Scenario: After launch

- **WHEN** search indexing is turned on and a crawler fetches `/robots.txt`
- **THEN** it allows the public pages, disallows `/admin/`, and names the sitemap, and the home page has no no-index instruction
