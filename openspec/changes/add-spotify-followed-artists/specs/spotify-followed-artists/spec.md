## Purpose

Lets a visitor connect their Spotify account and see which artists they follow have upcoming shows in the region, state or metro area they've chosen, without the site keeping their Spotify data.

## ADDED Requirements

### Requirement: Visitors can connect Spotify with the minimum scope
When the Spotify settings are configured, the site SHALL show a "Connect Spotify" link. The link SHALL start Spotify's Authorization Code flow with PKCE, with a random `state` value. It SHALL request only the `user-follow-read` scope, and it SHALL use the configured HTTPS redirect URI, or `http://127.0.0.1` during local development.

The callback SHALL:
- reject a `state` that doesn't match the one this session started with;
- exchange the code for tokens on the server;
- keep the tokens only in the visitor's server-side session;
- send the visitor to `/my-artists`.

The client secret and the tokens SHALL never appear in a page, a URL, a log line or an error message. When the Spotify settings aren't configured, the site SHALL show no Connect link, and the Spotify URLs SHALL return 404.

#### Scenario: Connect link starts PKCE authorization
- **WHEN** a visitor follows "Connect Spotify"
- **THEN** they're redirected to Spotify's authorize URL with `response_type=code`, `scope=user-follow-read`, a `code_challenge` with `code_challenge_method=S256`, a `state` value and the configured redirect URI

#### Scenario: Successful callback
- **WHEN** Spotify redirects back with a code and the matching `state`
- **THEN** the site exchanges the code for tokens, stores them in the session, and redirects to `/my-artists`

#### Scenario: Mismatched state
- **WHEN** the callback's `state` doesn't match the session's
- **THEN** no token exchange happens, no tokens are stored, and the visitor sees a message asking them to try connecting again

#### Scenario: Visitor declines on Spotify
- **WHEN** Spotify redirects back with `error=access_denied`
- **THEN** no tokens are stored, and `/my-artists` says that Spotify wasn't connected

#### Scenario: Spotify not configured
- **WHEN** `SPOTIFY_CLIENT_ID` is unset
- **THEN** no page shows a Connect link, and `/spotify/connect` returns 404

#### Scenario: Secrets stay out of pages
- **WHEN** any page renders for a connected visitor
- **THEN** the HTML contains neither the access token, the refresh token nor the client secret

### Requirement: Your-artists page shows followed artists' upcoming shows in the chosen area
For a connected visitor, `/my-artists` SHALL list upcoming approved events that name an artist the visitor follows on Spotify. The events SHALL appear in start-time order, grouped by date, each showing which followed artist it matched.

The page SHALL apply the visitor's region, state and metro filter from the `event-geo-filter` capability, read from the same URL parameters and the same remembered cookie as the events listing. It SHALL offer the same filter form. With no filter chosen, it SHALL include events in every area. It SHALL NOT ask for a ZIP code or the browser's location.

#### Scenario: Matches in the chosen state
- **WHEN** a connected visitor follows "Lake Street Dive" and has Vermont chosen, and Lake Street Dive has upcoming shows in Vermont and in Maine
- **THEN** `/my-artists` lists the Vermont show only, marked as matching Lake Street Dive

#### Scenario: No area chosen
- **WHEN** a connected visitor has no region, state or metro filter chosen
- **THEN** `/my-artists` lists matching upcoming events in every area

#### Scenario: Past and unapproved events excluded
- **WHEN** a followed artist has a past event and an upcoming event awaiting approval
- **THEN** neither appears on `/my-artists`

#### Scenario: No matches
- **WHEN** none of the visitor's followed artists has an upcoming event in the chosen area
- **THEN** the page says so, and links to the same page with the area filter cleared

#### Scenario: Not connected
- **WHEN** a visitor who hasn't connected Spotify opens `/my-artists`
- **THEN** the page explains the feature and shows the Connect Spotify link

### Requirement: Followed artists match event names by normalized whole names
An event SHALL match a followed artist when the artist's normalized name appears as a whole phrase in the event's normalized title or artists text. Normalizing SHALL:
- ignore case, accents and punctuation;
- treat "&" as "and";
- ignore a leading "The".

A followed artist whose normalized name is a single word of three letters or fewer SHALL match only when it is the event's entire title, or one entire comma-separated entry of its artists text.

#### Scenario: Match in the artists text
- **WHEN** the visitor follows "Psymon Spine" and an event's artists text is "SHEBAD, Psymon Spine"
- **THEN** the event matches Psymon Spine

#### Scenario: Match in the title, ignoring "The" and case
- **WHEN** the visitor follows "The Ballroom Thieves" and an event is titled "State Theatre Presents: the ballroom thieves"
- **THEN** the event matches The Ballroom Thieves

#### Scenario: Whole words only
- **WHEN** the visitor follows "Low" and an event is titled "Lowland Hum"
- **THEN** the event doesn't match Low

#### Scenario: Short name as a whole entry
- **WHEN** the visitor follows "Yes" and one event's artists text is "Yes", and another event is titled "Yes We Can Can: a Pointer Sisters tribute"
- **THEN** the first event matches Yes and the second doesn't

#### Scenario: Accents and ampersands
- **WHEN** the visitor follows "Beyoncé & Friends" and an event's artists text is "Beyonce and Friends"
- **THEN** the event matches

### Requirement: Spotify data is kept only briefly and deleted on disconnect
The site SHALL fetch the visitor's followed artists from Spotify, every page of them, and keep them in the session for at most one hour before fetching them again. It SHALL write no Spotify data to any database table other than the session. `/my-artists` SHALL offer a "Disconnect Spotify" button. Disconnecting SHALL delete the tokens and the followed-artist list from the session immediately, after which no Spotify request SHALL be made for that visitor.

#### Scenario: All pages of followed artists
- **WHEN** the visitor follows 120 artists, which Spotify returns as three pages
- **THEN** all 120 are used for matching

#### Scenario: Cached list reused within the hour
- **WHEN** the visitor reloads `/my-artists` 10 minutes after the last fetch
- **THEN** no request is made to Spotify

#### Scenario: Cache expires
- **WHEN** the visitor opens `/my-artists` more than an hour after the last fetch
- **THEN** the followed artists are fetched from Spotify again

#### Scenario: Disconnect
- **WHEN** a connected visitor presses Disconnect Spotify
- **THEN** the session no longer holds Spotify tokens or followed artists, `/my-artists` shows the Connect link, and no Spotify request is made

#### Scenario: Nothing stored outside the session
- **WHEN** a visitor connects and views `/my-artists`
- **THEN** no row outside the session table holds their Spotify tokens, user ID or followed artists

### Requirement: Spotify is credited and errors are explained
The page SHALL credit Spotify as the source of the followed-artist list, and link each matched artist name to that artist's Spotify page. It SHALL NOT suggest that Spotify endorses the site.

It SHALL handle Spotify's responses as follows:
- **An expired access token:** refresh it, and repeat the request once.
- **A failed refresh:** clear the Spotify data from the session, and ask the visitor to connect again.
- **403:** show a message saying that this site's Spotify connection is limited to invited testers. The message SHALL include the text of Spotify's error.
- **429:** wait as long as the `Retry-After` header says, backing off exponentially, for at most three tries. After that, show a "Spotify is busy, try again shortly" message instead of failing the page.

#### Scenario: Token refreshed transparently
- **WHEN** Spotify returns 401 for the followed-artists request, and the refresh token is still valid
- **THEN** the site refreshes the access token, repeats the request, and shows the matches

#### Scenario: Refresh token revoked
- **WHEN** the refresh request fails with `invalid_grant`
- **THEN** the Spotify data is cleared from the session, and the page asks the visitor to connect again

#### Scenario: Visitor not on the tester list
- **WHEN** Spotify answers 403 because the visitor's account isn't registered for this development-mode app
- **THEN** the page explains that Spotify connection is currently limited to invited testers

#### Scenario: Rate limited
- **WHEN** Spotify answers 429 with `Retry-After: 2`, and then succeeds
- **THEN** the site waits at least 2 seconds before retrying, and shows the matches

#### Scenario: Rate limited repeatedly
- **WHEN** Spotify answers 429 three times in a row
- **THEN** the page shows the "Spotify is busy" message, with status 200

#### Scenario: Attribution
- **WHEN** a connected visitor has matches
- **THEN** each matched artist name links to `https://open.spotify.com/artist/<id>`, and the page credits Spotify as the source
