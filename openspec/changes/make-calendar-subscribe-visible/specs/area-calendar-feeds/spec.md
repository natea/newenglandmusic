## MODIFIED Requirements

### Requirement: Visitors can subscribe from the listing
Near the top of the homepage and month archive pages, above the area filter, the page SHALL show a visible "Subscribe" button for the area chosen, or for all areas when none is chosen, naming the area when one is chosen (for example "Subscribe: Vermont"). Opening it SHALL offer:
- a `webcal://` link to the feed;
- a link that adds the feed in Google Calendar by URL;
- the feed's `https://` URL to copy;
- a note that calendar apps check for new shows on their own schedule and Google can take up to a day.

It SHALL work without JavaScript.

#### Scenario: Subscribe to a state
- **WHEN** a visitor has Vermont chosen
- **THEN** the subscribe links point at `/calendar.ics?state=vermont`, with `webcal://` for the app link, the Google Calendar link adds that URL, and the button names Vermont

#### Scenario: Nothing chosen
- **WHEN** no area is chosen
- **THEN** the subscribe links point at `/calendar.ics`, with no parameters

#### Scenario: Seen before the filter
- **WHEN** a visitor opens the homepage or a month archive page
- **THEN** the Subscribe button comes before the area filter in the page, without anything needing to be opened first

#### Scenario: Without JavaScript
- **WHEN** the page is used with JavaScript off
- **THEN** the button opens its panel of links and address
