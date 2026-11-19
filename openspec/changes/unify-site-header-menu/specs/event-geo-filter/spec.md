## ADDED Requirements

### Requirement: The listing's filter and location controls fold away

On the listing pages (not Discover or saved shows), the state, metro and town filter and the "near" location form SHALL sit in one section that is collapsed on load, and the calendar-subscribe box SHALL be collapsed on load. A summary line SHALL show what applies, with the "show all" link beside it when a filter applies. The section SHALL never open by itself. The section SHALL be left out when neither control renders. The section SHALL work without JavaScript.

#### Scenario: Collapsed by default

- **WHEN** a visitor with no remembered filter opens the home page
- **THEN** the filter and location form are inside a collapsed section, and the subscribe box is collapsed

#### Scenario: The summary says what applies

- **WHEN** a visitor with a state filter and a saved location opens the home page
- **THEN** the collapsed section's summary names the state and the location, the "show all" link is visible without opening it, and the section is still closed, and opening it shows the filter and form with those values chosen

#### Scenario: Only one control, or none

- **WHEN** no states are loaded and census places are loaded, or the reverse, or neither
- **THEN** the section is titled for the one control that shows, or is not on the page at all, and no empty fold appears

#### Scenario: Month archive

- **WHEN** a visitor opens a month archive
- **THEN** it shows the same collapsed section and summary as the listing

#### Scenario: Opening it

- **WHEN** a visitor opens the section and submits the filter
- **THEN** the page reloads filtered, and the filter still works as before, including the remembered-filter cookie

#### Scenario: Without JavaScript

- **WHEN** JavaScript is off
- **THEN** the section opens and closes, and the filter and location forms, each with a submit button, submit as plain forms
