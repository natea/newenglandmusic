## ADDED Requirements

### Requirement: The site is named Stagehopper

The site's name SHALL come from `SITE_NAME`, which defaults to "Stagehopper" (Nate's decision, 11 November 2026). The name SHALL appear in the masthead, every page's title and link preview, the admin's header, the privacy page, and each event's calendar entry, which is named for the event followed by "[Stagehopper]".

#### Scenario: The masthead and title

- **WHEN** a visitor opens the home page with `SITE_NAME` unset
- **THEN** the masthead reads "Stagehopper", and the page's title and its Open Graph title name "Stagehopper"

#### Scenario: A name from the setting

- **WHEN** `SITE_NAME` is "Boston Shows"
- **THEN** the masthead, the admin's header and an event's calendar entry use "Boston Shows"

#### Scenario: An event's calendar entry

- **WHEN** the single-event download of "Dummy Ache at The Press Room" is fetched with `SITE_NAME` unset
- **THEN** its entry is named "Dummy Ache at The Press Room [Stagehopper]"

### Requirement: The masthead carries a tagline

Under the name, the masthead SHALL show a tagline from `SITE_TAGLINE`, which defaults to "Live music across New England". An empty tagline SHALL show nothing.

#### Scenario: The default tagline

- **WHEN** a visitor opens any page with `SITE_TAGLINE` unset
- **THEN** the masthead shows "Live music across New England" under "Stagehopper"

#### Scenario: No tagline

- **WHEN** `SITE_TAGLINE` is set to a single space
- **THEN** the masthead shows the name alone

### Requirement: The site's address comes from SITE_URL

Production SHALL serve the site at `SITE_URL`, https://stagehopper.app, and accept the hosts stagehopper.app, www.stagehopper.app and the service's own onrender.com address. The contact address the site's API clients send SHALL come from `SITE_URL`, not a fixed address.

#### Scenario: The API clients' contact address

- **WHEN** `SITE_URL` is https://stagehopper.app and the site's MusicBrainz client builds its user agent
- **THEN** the user agent names https://stagehopper.app

### Requirement: Other addresses redirect to the site's address

A request whose host isn't `SITE_URL`'s SHALL be redirected permanently (301) to the same path and query at `SITE_URL`. Three kinds of request SHALL be served directly instead, at any allowed host: a calendar feed, so existing subscriptions keep working; an event's calendar download; and the health check at `/health`, which answers 200 with no page. Nothing SHALL be redirected while `SITE_URL` is unset or names the request's own host.

#### Scenario: The old address

- **WHEN** a visitor opens `https://newenglandmusic.onrender.com/bands?state=VT` with `SITE_URL` https://stagehopper.app
- **THEN** they get a 301 to `https://stagehopper.app/bands?state=VT`

#### Scenario: The www address

- **WHEN** a visitor opens `https://www.stagehopper.app/` with `SITE_URL` https://stagehopper.app
- **THEN** they get a 301 to `https://stagehopper.app/`

#### Scenario: A subscribed calendar on the old address

- **WHEN** a calendar app fetches `https://newenglandmusic.onrender.com/calendar.ics?state=VT`
- **THEN** it gets the feed itself, with a 200, not a redirect

#### Scenario: The health check

- **WHEN** Render's health check requests `/health` at any allowed host
- **THEN** it gets a 200, not a redirect

#### Scenario: Development

- **WHEN** `SITE_URL` is `http://localhost:8001` and a request comes to `localhost:8001`
- **THEN** nothing is redirected

### Requirement: The landing page's old addresses redirect

`/privacy.html` and `/terms.html`, which stagehopper.app served for Stagehopper's landing page before the move, SHALL redirect permanently to the site's own `/privacy` and `/terms`.

#### Scenario: An old privacy link

- **WHEN** a visitor opens `https://stagehopper.app/privacy.html`
- **THEN** they get a 301 to `https://stagehopper.app/privacy`

### Requirement: Every page links the privacy and terms pages

The footer of every page SHALL link `/privacy` and `/terms`. The terms page SHALL say what the site is, what visitors may and may not do with it, that listings come from venues and other sources and may be wrong, and how to contact the site. The privacy page SHALL say what email addresses the site keeps (an event submitter's, a subscriber's), why, who can see them, and how to have one removed. Both SHALL name the site by `SITE_NAME`.

#### Scenario: The footer

- **WHEN** a visitor opens any page
- **THEN** its footer links both "Privacy" and "Terms"

#### Scenario: The terms page

- **WHEN** a visitor opens `/terms` with `SITE_NAME` unset
- **THEN** the page names "Stagehopper" and includes how to contact the site

#### Scenario: Email addresses on the privacy page

- **WHEN** a visitor opens `/privacy`
- **THEN** it has a section on email addresses that covers submitters' and subscribers' addresses and how to have one removed
