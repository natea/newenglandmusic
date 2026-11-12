## ADDED Requirements

### Requirement: The site is named Stagehopper

The site's name SHALL come from `SITE_NAME`, which defaults to "Stagehopper" (Nate's decision, 11 November 2026). The name SHALL appear in the masthead, every page's title and link preview, the admin's header, and each event's calendar entry, which is named for the event followed by "[Stagehopper]".

#### Scenario: The masthead and title

- **WHEN** a visitor opens the home page with `SITE_NAME` unset
- **THEN** the masthead reads "Stagehopper", and the page's title and its Open Graph title name "Stagehopper"

#### Scenario: A name from the setting

- **WHEN** `SITE_NAME` is "Boston Shows"
- **THEN** the masthead, the admin's header and an event's calendar entry use "Boston Shows"

#### Scenario: An event's calendar entry

- **WHEN** the single-event download of an event whose title and artists read "Dummy Ache" is fetched with `SITE_NAME` unset
- **THEN** its entry is named "Dummy Ache [Stagehopper]"

### Requirement: The masthead carries a tagline

Under the name, the masthead SHALL show a tagline from `SITE_TAGLINE`, which defaults to "Live music across New England". A blank or whitespace-only tagline SHALL show nothing.

#### Scenario: The default tagline

- **WHEN** a visitor opens any page with `SITE_TAGLINE` unset
- **THEN** the masthead shows "Live music across New England" under "Stagehopper"

#### Scenario: No tagline

- **WHEN** `SITE_TAGLINE` is set to a single space
- **THEN** the masthead shows the name alone

### Requirement: The site's address comes from SITE_URL

Production SHALL accept as hosts stagehopper.app and www.stagehopper.app, whatever `ALLOWED_HOSTS` adds, and the service's own onrender.com address. The contact address the site's API clients send SHALL come from `SITE_URL`, not a fixed address, in the web service and in the scheduled jobs alike.

#### Scenario: Production's hosts

- **WHEN** the production settings load with `RENDER_EXTERNAL_HOSTNAME` "newenglandmusic.onrender.com" and `ALLOWED_HOSTS` unset
- **THEN** the allowed hosts include stagehopper.app, www.stagehopper.app and newenglandmusic.onrender.com

#### Scenario: The API clients' contact address

- **WHEN** `SITE_URL` is https://stagehopper.app and the site's MusicBrainz client builds its user agent
- **THEN** the user agent names https://stagehopper.app

### Requirement: Other addresses redirect to the site's address

When `CANONICAL_HOST` is set (production sets it to stagehopper.app), a request on any other host SHALL be redirected permanently (301) to the same path and query at `SITE_URL`, built from `SITE_URL` alone, never from the request's Host header. The health check SHALL be served at any allowed host instead. While `CANONICAL_HOST` is empty, its default, nothing SHALL be redirected, so tests, development and previews behave as before.

#### Scenario: The old address

- **WHEN** a visitor opens `https://newenglandmusic.onrender.com/bands?state=VT` with `CANONICAL_HOST` stagehopper.app and `SITE_URL` https://stagehopper.app
- **THEN** they get a 301 to `https://stagehopper.app/bands?state=VT`

#### Scenario: The www address

- **WHEN** a visitor opens `https://www.stagehopper.app/` with `CANONICAL_HOST` stagehopper.app
- **THEN** they get a 301 to `https://stagehopper.app/`

#### Scenario: A calendar feed on the old address

- **WHEN** a calendar app fetches `https://newenglandmusic.onrender.com/calendar.ics?state=VT` with `CANONICAL_HOST` stagehopper.app
- **THEN** it gets a 301 to `https://stagehopper.app/calendar.ics?state=VT`

#### Scenario: No canonical host

- **WHEN** `CANONICAL_HOST` is empty and a request comes to `127.0.0.1:8001`, or to the test client's host
- **THEN** nothing is redirected

### Requirement: A redirected form keeps its method

A redirect from another host of a request that isn't GET or HEAD SHALL be a 308 instead of a 301, so a form submitted to an old address keeps its method and body.

#### Scenario: A form posted to the old address

- **WHEN** a form is posted to `https://newenglandmusic.onrender.com/submit-event` with `CANONICAL_HOST` stagehopper.app
- **THEN** it gets a 308 to `https://stagehopper.app/submit-event`

### Requirement: The health check answers at its own path

`/health` SHALL answer 200 with the plain body "ok", at any allowed host, without reading the database.

#### Scenario: The health check

- **WHEN** Render's health check requests `/health` on the onrender.com address with `CANONICAL_HOST` stagehopper.app
- **THEN** it gets a 200 with the body "ok", not a redirect

### Requirement: The landing page's old paths go to its new address

When `CANONICAL_HOST` is set, the paths StageHopper's landing page served at stagehopper.app before the move SHALL redirect permanently to the same path and query at https://info.stagehopper.app. These are its top-level pages (`.html`), data files (`.json`, `.geojson`) and preview images (`og.png`, `og_boston.png`, `og_nyc.png`), and anything under `/boston/` and `/nyc/`. The site's own pages use none of these paths.

#### Scenario: The landing page's privacy policy

- **WHEN** a visitor, or an app's privacy link, opens `https://stagehopper.app/privacy.html` with `CANONICAL_HOST` stagehopper.app
- **THEN** they get a 301 to `https://info.stagehopper.app/privacy.html`

#### Scenario: A landing map

- **WHEN** a visitor opens `https://stagehopper.app/events_map_boston.html` with `CANONICAL_HOST` stagehopper.app
- **THEN** they get a 301 to `https://info.stagehopper.app/events_map_boston.html`

#### Scenario: The site's own privacy page

- **WHEN** a visitor opens `https://stagehopper.app/privacy` with `CANONICAL_HOST` stagehopper.app
- **THEN** they get the site's privacy page, not a redirect

### Requirement: The site has a terms page and says how it handles email addresses

Every page's footer SHALL link `/terms`, beside the `/privacy` link that `youtube-artist-preview` requires. Both pages SHALL name the site by `SITE_NAME`. The terms page SHALL say:
- what the site is;
- what visitors may and may not do with it;
- that listings come from venues and other sources and may be wrong;
- how to contact the site.

The privacy page SHALL say what email addresses the site keeps (an event submitter's, a subscriber's), why, who can see them, and how to have one removed.

#### Scenario: The footer

- **WHEN** a visitor opens any page
- **THEN** its footer links "Terms" beside "Privacy"

#### Scenario: The terms page

- **WHEN** a visitor opens `/terms` with `SITE_NAME` unset
- **THEN** the page names "Stagehopper" and includes how to contact the site

#### Scenario: Email addresses on the privacy page

- **WHEN** a visitor opens `/privacy`
- **THEN** it has a section on email addresses that covers submitters' and subscribers' addresses and how to have one removed

#### Scenario: Both pages follow the setting

- **WHEN** `SITE_NAME` is "Boston Shows" and a visitor opens `/terms` and `/privacy`
- **THEN** both pages name "Boston Shows", not "Stagehopper"
