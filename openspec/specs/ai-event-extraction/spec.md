# ai-event-extraction Specification

## Purpose
Turns the visible text of a venue's web page into structured upcoming events using Claude, for venues that publish no feed or structured event data, while keeping cost low and avoiding invented details.

## Requirements

### Requirement: Page text is prepared for extraction
The page sent for extraction SHALL be its visible text without scripts, styles, frames or head content. Each link's absolute URL SHALL be kept next to its text, and the text SHALL be capped at 150,000 characters, with truncation reported.

#### Scenario: Event link in the page
- **WHEN** a page has a link "Tickets" to `/events/42`
- **THEN** the text sent includes "Tickets <https://venue.example/events/42>"

#### Scenario: Very long page
- **WHEN** a page's text exceeds 150,000 characters
- **THEN** it is cut to that length and the venue's report notes the truncation

### Requirement: Extraction returns only events the page shows
The extraction SHALL return upcoming events at the venue as written on the page, as structured JSON. It SHALL leave out past events, other venues' events, business hours and promotions. Fields the page doesn't give SHALL be left empty rather than guessed.

#### Scenario: Page with no events
- **WHEN** a page lists only recurring opening hours
- **THEN** no events are returned

#### Scenario: Support act
- **WHEN** the page lists "Samantha Fish w/ Sgt. Splendor"
- **THEN** the event's title is "Samantha Fish" and its artists are "Sgt. Splendor"

### Requirement: Extracted fields are validated
An extracted event with an unparseable date or a placeholder title SHALL be dropped. A missing or invalid time SHALL make the event all-day. The year SHALL be the next one matching the page's date on or after today. Prices written as text SHALL be parsed, with "Free" as 0.

#### Scenario: Invalid date
- **WHEN** the model returns start_date "TBD"
- **THEN** that event is dropped and the rest are kept

#### Scenario: Price text
- **WHEN** the price is "$20 adv / $25 door"
- **THEN** the event's price amount is 20

### Requirement: Extracted events get stable IDs
An extracted event's external ID SHALL be built from its own URL and start time, or from the page URL, title and start time when it has no URL. Re-extracting the same event SHALL then update it.

#### Scenario: Weekly night sharing one page
- **WHEN** a page lists "Jazz Jam" on three dates with no individual links
- **THEN** three events with different external IDs are saved

### Requirement: The model is cheap by default and selectable
Extraction SHALL use `claude-haiku-5-5` by default, and a different model SHALL be selectable per run. Server-side fallback SHALL be requested only for models that support it.

#### Scenario: Default run
- **WHEN** the import runs without `--model`
- **THEN** pages are extracted with claude-haiku-5-5 and the token usage is reported per venue and in total

### Requirement: Extraction failures don't stop the import
Without an API key, or with `--skip-ai`, pages SHALL be skipped with a note. An API error, malformed output or a response that stops early SHALL be reported for that venue, and the run SHALL continue.

#### Scenario: No API key
- **WHEN** the import runs without `ANTHROPIC_API_KEY`
- **THEN** AI pages are reported as skipped and events from other sources are still saved

#### Scenario: Output cut off
- **WHEN** a response stops for a reason other than finishing its turn
- **THEN** that venue is reported as failed and no partial events from it are saved
