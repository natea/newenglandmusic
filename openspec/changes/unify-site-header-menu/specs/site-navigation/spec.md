## ADDED Requirements

### Requirement: One menu on every page

Every page that extends the site's base template SHALL show the same site menu, made of the admin's menu items marked to show in the header, in their admin order, followed by the fixed "Saved shows" link. The menu SHALL be a `nav` with a stable id. The menu SHALL be one list: no page SHALL show a second, different list of links beside it.

#### Scenario: The same menu on every page

- **WHEN** a visitor opens the listing, a month archive, a search, Discover, the act index, a band page, a venue page, saved shows and a static page
- **THEN** the menu markup is identical on each

#### Scenario: One list only

- **WHEN** a visitor opens the home page
- **THEN** the page holds one menu list, and no separate hidden list of all menu items

#### Scenario: Edited in the admin

- **WHEN** an editor renames a menu item or turns off its "show in header" setting
- **THEN** the change shows in the menu on every page

### Requirement: Links across the top on wide screens

On a wide screen the menu SHALL show its links across the top of the page, with the "Saved shows" link among them, and no ☰ button.

#### Scenario: Computer

- **WHEN** a visitor opens any page in a wide browser window
- **THEN** the links are visible across the top and the ☰ button is not shown

### Requirement: A ☰ button on narrow screens

On a narrow screen the menu SHALL show a single ☰ button in place of the links. Activating it SHALL open the same links as a stacked column, and activating it again SHALL close it. The button SHALL be a real button with an accessible name, and SHALL say whether the menu is open.

#### Scenario: Phone, closed

- **WHEN** a visitor opens any page in a phone-sized window
- **THEN** the links are hidden and the ☰ button is shown, marked as closed

#### Scenario: Phone, opened

- **WHEN** the visitor activates the ☰ button
- **THEN** the same links show stacked one to a line, none squeezed together, and the button is marked as open

#### Scenario: Closed again

- **WHEN** the visitor activates the button a second time
- **THEN** the links hide again

#### Scenario: Keyboard

- **WHEN** a visitor focuses the ☰ button and presses Enter or Space
- **THEN** the menu opens or closes as for a tap

### Requirement: The menu works without JavaScript

Without JavaScript the links SHALL stay reachable on every screen width: the list is shown and the ☰ button is not.

#### Scenario: No script on a phone

- **WHEN** a visitor on a phone-sized window has JavaScript turned off
- **THEN** every menu link is shown, the ☰ button is not, and no link is hidden for good

### Requirement: The menu reaches the main pages

The menu SHALL link to every menu item marked to show in the header, so the listing, venues, artists, about and Discover pages are reachable once editors mark their items.

#### Scenario: The main links

- **WHEN** menu items named for the listing, venues, artists, about and Discover exist, each marked to show in the header, and a visitor opens the home page
- **THEN** the menu links to each of those pages
