# site-analytics Specification

## Purpose
Lets the site's editors see how the site is used (what visitors search for, open, save, play and follow through to tickets) with PostHog and GoatCounter, while sending nothing that identifies a person, and telling visitors so on the privacy page.

## Requirements

### Requirement: PostHog is switched on by its settings
Every public page SHALL load PostHog when `POSTHOG_PROJECT_TOKEN` is set, sending to the PostHog host `POSTHOG_HOST` names. With no project key, no page SHALL load PostHog or contact PostHog's servers. The admin SHALL never load PostHog.

#### Scenario: Switched on
- **WHEN** `POSTHOG_PROJECT_TOKEN` is set and a visitor opens any public page
- **THEN** the page loads PostHog with that key and host

#### Scenario: Switched off
- **WHEN** `POSTHOG_PROJECT_TOKEN` is empty
- **THEN** no page includes PostHog

#### Scenario: Not in the admin
- **WHEN** an editor opens an admin page with PostHog switched on
- **THEN** the admin page doesn't include PostHog

### Requirement: Pageviews and the site's key actions are recorded
With PostHog switched on, the site SHALL record each pageview and autocaptured clicks, and these named events with their properties:
- `search` when a full search runs (the words searched);
- `search_suggestion_chosen` when a suggestion is chosen (its kind: band, artist, venue or show; and the words typed);
- `search_results_viewed` when a search results page is shown (the words searched; how many bands and artists, venues, upcoming shows, past shows and pages matched; and the total);
- `act_page_viewed` when a band's or artist's page is shown (its name, its kind, and whether it has an upcoming show);
- `show_saved` and `show_unsaved` when a show's bookmark is pressed (the show's ID and name);
- `preview_played` when a play button is pressed (its service: Spotify, Apple Music or YouTube);
- `ticket_link_opened` when a show's ticket link is followed (the show's ID and name);
- `show_added_to_calendar` when a show's calendar file or Google Calendar link is followed (which one, and the show's ID and name);
- `calendar_feed_subscribed` when a calendar feed's subscribe link is followed;
- `deck_act_passed` and `deck_shows_saved` when an act is passed in the discovery deck, or shows are saved from it (the number saved).

A show's name SHALL be its title and artists as the listing prints them.

#### Scenario: A search
- **WHEN** a visitor searches for "belly"
- **THEN** a `search` event is recorded with the words "belly"

#### Scenario: A suggestion chosen
- **WHEN** a visitor types "bel" and chooses the band Belly
- **THEN** a `search_suggestion_chosen` event is recorded with the kind "band" and the words "bel"

#### Scenario: A show saved
- **WHEN** a visitor presses a show's bookmark
- **THEN** a `show_saved` event is recorded with that show's ID and name, and pressing it again records `show_unsaved`

#### Scenario: A play button
- **WHEN** a visitor presses a Spotify play button
- **THEN** a `preview_played` event is recorded with the service "spotify"

#### Scenario: A ticket link
- **WHEN** a visitor follows a show's "tix" link
- **THEN** a `ticket_link_opened` event is recorded with that show's ID and name

#### Scenario: A search that finds nothing
- **WHEN** a visitor's search for "zzzz" finds nothing
- **THEN** a `search_results_viewed` event is recorded with the words "zzzz" and a total of 0

#### Scenario: A search's counts
- **WHEN** a search for "belly" finds one band, no venues, two upcoming shows and one past show
- **THEN** `search_results_viewed` records those counts and a total of 4

#### Scenario: An act page
- **WHEN** a visitor opens Belly's page, and Belly has an upcoming show
- **THEN** an `act_page_viewed` event is recorded with the name "Belly", the kind "band" and that it has an upcoming show

### Requirement: Nothing that identifies a person is sent
The site SHALL NOT send PostHog a name, an email address, the location a visitor gives for distances (a ZIP code, town or their position) or a distance, or the contents of any form field other than the search words; it SHALL NOT identify visitors as people, SHALL NOT record sessions, and SHALL keep anonymous visitors out of PostHog's person profiles. PostHog SHALL keep one first-party cookie to recognise a returning browser, and SHALL discard each visitor's IP address after working out their approximate location from it, so the address is never stored.

#### Scenario: A submission's email stays out
- **WHEN** a visitor submits an event with their email address
- **THEN** nothing PostHog records holds the address

#### Scenario: No session recording
- **WHEN** PostHog loads on any page
- **THEN** session recording is off

### Requirement: Visitors can turn analytics off
The privacy page SHALL say that the site uses PostHog, what it records (pages opened and the key actions above), that it sets a cookie to recognise a returning browser, that it works out an approximate city and region from the IP address and then discards the address, and that it records no names, emails or IP addresses; and it SHALL offer a control that turns PostHog off in that browser, and back on. A browser that has turned it off SHALL send PostHog nothing.

#### Scenario: Turning it off
- **WHEN** a visitor turns analytics off on the privacy page and then searches
- **THEN** no event is sent to PostHog from that browser

#### Scenario: The privacy page describes it
- **WHEN** a visitor opens `/privacy` with PostHog switched on
- **THEN** it names PostHog, says it sets a cookie, and offers the control to turn it off

### Requirement: GoatCounter counts pages when switched on
When `GOATCOUNTER_CODE` is set, every public page SHALL load GoatCounter's counter for that code; with none, no page SHALL load it. GoatCounter SHALL set no cookie.

#### Scenario: GoatCounter switched on
- **WHEN** `GOATCOUNTER_CODE` is "stagehopper"
- **THEN** each public page loads the counter for `https://stagehopper.goatcounter.com/count`
