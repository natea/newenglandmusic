## MODIFIED Requirements

### Requirement: Filters survive navigation and bad input
The previous, current and next month links SHALL keep the chosen filters and any picked `genre`. An unknown or stale filter value SHALL be ignored, as though it wasn't given, and SHALL NOT cause an error page.

#### Scenario: Month links keep the filter
- **WHEN** a visitor on `/?state=maine` follows the next-month link
- **THEN** the next month's archive opens with `state=maine` still applied

#### Scenario: Unknown value
- **WHEN** a visitor opens `/?state=atlantis`
- **THEN** the page returns 200 and lists events from every venue

### Requirement: The site remembers a visitor's last filter
The site SHALL remember a visitor's last filter in a first-party cookie, so that a later visit opens with the same filter applied.
- **Setting the cookie:** when a listing page is opened with at least one valid filter, the response SHALL save the resolved filter in the cookie. The cookie SHALL expire after one year.
- **Using the cookie:** when the homepage or a month archive is opened with no `region`, `state`, `metro` or `clear` parameter and the cookie holds a valid filter, the response SHALL redirect to the same page with that filter's parameters, and SHALL keep a `genre` value if the address had one (a `genre` alone is not a filter parameter: it neither counts as one, sets the cookie, nor prevents the redirect).
- **Clearing the cookie:** opening a listing page with `clear` set, or with the filter parameters present but all empty, SHALL delete the cookie and show the unfiltered listing.
- **Stale values:** a cookie whose values no longer match any offered area SHALL be deleted, without a redirect.
- **Other pages:** the cookie SHALL NOT affect search results or any other page.

#### Scenario: Filter is remembered
- **WHEN** a visitor opens `/?state=vermont` and later opens `/`
- **THEN** the second request redirects to `/?state=vermont`

#### Scenario: Remembered filter on a month archive
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/2026-11/`
- **THEN** the request redirects to `/2026-11/?state=vermont`

#### Scenario: A shared link wins over the cookie
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/?state=maine`
- **THEN** Maine events are listed, and the cookie now holds `state=maine`

#### Scenario: Clearing the filter
- **WHEN** a visitor with a remembered filter sets every filter to "All", or follows the "show all" link
- **THEN** the unfiltered listing is shown, the cookie is deleted, and a later visit to `/` isn't redirected

#### Scenario: Stale cookie
- **WHEN** a visitor's cookie holds the slug of a metro that has since been removed from the sheet
- **THEN** `/` shows the unfiltered listing with no redirect, and the cookie is deleted

#### Scenario: No filter chosen
- **WHEN** a visitor who has never chosen a filter opens `/`
- **THEN** no cookie is set and the page isn't redirected

#### Scenario: Search ignores the cookie
- **WHEN** a visitor with a remembered filter searches with `/?s=jazz`
- **THEN** the search results aren't filtered and the request isn't redirected

#### Scenario: Genre kept through the redirect
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/?genre=jazz`
- **THEN** the request redirects to an address with both `state=vermont` and `genre=jazz`
