## MODIFIED Requirements

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
