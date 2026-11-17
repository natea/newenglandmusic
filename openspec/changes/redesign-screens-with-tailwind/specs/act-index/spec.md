# Spec Delta

## MODIFIED Requirements

### Requirement: The search box is at the top of every page
The search box SHALL be in the header of every page, beside the site's name, not behind a menu. On the search results page it SHALL hold what was searched, and the page SHALL have no other search box.

#### Scenario: On every page
- **WHEN** a visitor opens any page
- **THEN** the search box is in view in the header, without opening a menu

#### Scenario: One box on the results page
- **WHEN** a visitor searches for "belly"
- **THEN** the results page has one search box, holding "belly", and it suggests as the others do

## REMOVED Requirements

### Requirement: The index is set like a book's index
**Reason**: The new design sets each letter as one run of entries under a single guide line, and prints names as they are; 40-entry pages and the inverted "The" belonged to the book-index look.
**Migration**: None for visitors. "Each letter opens with a guide line" below takes its place; acts are still filed ignoring a leading "The".

## ADDED Requirements

### Requirement: Each letter opens with a guide line
Each letter SHALL open with its large initial, the number of acts under it, and one guide line naming its first and last acts ("184 acts · Bark At The Moon to Byrne Bros"), over its entries in two columns at 1024px wide and up and one column below. A name starting "The" SHALL be filed ignoring it and printed as the act's own name ("The Blue Stones", under B).

#### Scenario: A letter's guide line
- **WHEN** the letter B has 184 acts, the first "Bark At The Moon" and the last "Byrne Bros"
- **THEN** B's section opens with "B", "184 acts" and "Bark At The Moon to Byrne Bros", once

#### Scenario: "The" names filed without it, printed with it
- **WHEN** the site has "The Atlantics"
- **THEN** the index lists it under A, printed "The Atlantics", and its page and a search for it print "The Atlantics"
