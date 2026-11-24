## Purpose
Gives multi-day events such as Porchfest a record of their own: a title, dates and a description, a public page, one multi-day entry in the calendar, and the shows that belong to it, attached automatically and correctable by editors.

## ADDED Requirements

### Requirement: Editors keep festivals in the admin
A festival SHALL have a title, a start date, an end date and a description, and SHALL be created, edited and deleted in the admin. The end date SHALL NOT be before the start date. The title is required; the description MAY be empty. Each festival SHALL have a slug made from its title once, unique across festivals. Deleting a festival SHALL leave its shows in place with no festival, return them all to automatic matching, and re-render their stored rows.

#### Scenario: Create a festival
- **WHEN** an editor saves a festival "Somerville Porchfest" from 2026-09-26 to 2026-09-27 with a description
- **THEN** the festival exists with the slug `somerville-porchfest`

#### Scenario: One-day festival
- **WHEN** an editor saves a festival whose start and end dates are the same
- **THEN** it is saved, and counts as one day long

#### Scenario: End before start
- **WHEN** an editor saves a festival whose end date is before its start date
- **THEN** the admin refuses it with an error on the end date

#### Scenario: Same title twice
- **WHEN** a second festival is saved with the title "Somerville Porchfest"
- **THEN** its slug is `somerville-porchfest-2`

#### Scenario: Deleting a festival
- **WHEN** an editor deletes a festival that has shows
- **THEN** the shows still exist and belong to no festival, and their rows no longer link to it

#### Scenario: Deleting a festival frees editor-attached shows
- **WHEN** an editor deletes a festival that an editor had attached a show to
- **THEN** the show is set automatically again, not marked as not part of any festival, and a later matching festival can attach it

### Requirement: A festival has a public page
The site SHALL serve each festival at `/festivals/<slug>`, showing its title, its dates (as one date when start and end are the same, otherwise a range), its description and its approved shows night by night, in start order. A festival with no shows SHALL still have its page, saying no shows are listed yet. An unknown slug SHALL answer 404.

#### Scenario: Page content
- **WHEN** a visitor opens the page of a festival with two approved shows on its second day
- **THEN** the page shows the title, the date range, the description and both shows under that day

#### Scenario: Unapproved show
- **WHEN** a festival has an unapproved show
- **THEN** the page doesn't list it

#### Scenario: No shows yet
- **WHEN** a visitor opens a festival's page and none of its shows is approved
- **THEN** the page shows the title, dates and description and a note that no shows are listed yet

#### Scenario: Unknown festival
- **WHEN** a visitor opens `/festivals/nothing-here`
- **THEN** the site answers 404

### Requirement: Festival pages are indexable and outlast the festival
A festival's page SHALL be indexable and have a canonical link, and every festival SHALL be in the sitemap. A festival whose end date has passed (New York time) SHALL keep its page, marked as past.

#### Scenario: Past festival
- **WHEN** a visitor opens the page of a festival that ended yesterday
- **THEN** the page is served, marked as past

#### Scenario: Listed in the sitemap
- **WHEN** the sitemap is read
- **THEN** it includes every festival's page address

#### Scenario: Canonical link
- **WHEN** a visitor opens a festival's page
- **THEN** the page has a canonical link to its own address and no noindex

### Requirement: The calendar shows a festival as one multi-day entry
The home listing and the month archives SHALL show each festival that overlaps the days on screen once, as an entry linking to its page, giving its title and its date range. The entry SHALL appear on the first day on screen that the festival covers, at the top of that day, and SHALL NOT repeat on its later days. A festival's shows SHALL still be listed on their own days.

#### Scenario: Entry on the first day
- **WHEN** the home listing covers a festival running Saturday to Sunday and both days are on screen
- **THEN** one entry appears at the top of Saturday, naming the festival and its range, and Sunday has none

#### Scenario: Festival already running
- **WHEN** a festival started two days ago and ends tomorrow
- **THEN** the home listing shows its entry once, at the top of today, with its full range

#### Scenario: Shows keep their days
- **WHEN** a festival has a show on Sunday
- **THEN** that show is listed under Sunday as usual

#### Scenario: Month archive
- **WHEN** a visitor opens the archive of a month a festival ends in
- **THEN** the entry appears once, on the festival's first day in that month

#### Scenario: Outside the window
- **WHEN** a festival ended before the days on screen start, or starts after they end
- **THEN** it has no entry

### Requirement: The calendar entry follows the area filter
A festival's entry SHALL be left out of a listing filtered to an area when none of the festival's shows' venues belong to that area. A festival with no shows SHALL be left out of a filtered listing and shown in an unfiltered one. Attached shows count whether approved or not, and a show counts only if its venue is in the area. The unfiltered listing SHALL show every festival that overlaps the days on screen.

#### Scenario: Area filter
- **WHEN** a visitor filters to an area where none of a festival's shows' venues are
- **THEN** the festival's entry isn't shown

#### Scenario: Festival with no shows
- **WHEN** a festival has no shows
- **THEN** its entry shows in the unfiltered listing and not in a filtered one

#### Scenario: Only unapproved shows in the area
- **WHEN** a festival's only show in the area is unapproved
- **THEN** its entry is shown in that area's listing

### Requirement: Shows attach to festivals automatically
When a show with a start time is saved, approved or not, and when a festival's dates or match words change, the site SHALL attach the show to a festival if the show's start, in New York time, falls on or between the festival's start and end dates, and the festival's match words occur in the show's title, its artists text or its venue's town, ignoring case and surrounding whitespace. A show attached automatically SHALL be recorded as set automatically.

#### Scenario: Matches by title in the dates
- **WHEN** a show titled "Porchfest: The Bees" starts on a festival's second day and the festival is "Porchfest"
- **THEN** the show is attached to the festival, set automatically

#### Scenario: Right words, wrong dates
- **WHEN** a show titled "Porchfest preview" starts the week before the festival's start date
- **THEN** it isn't attached

#### Scenario: Town restricts the match
- **WHEN** a festival "Porchfest" names the town Somerville and a show titled "Porchfest" is at a venue in Cambridge on a festival day
- **THEN** it isn't attached

#### Scenario: Late-night show on the last day
- **WHEN** a show starts at 11:30pm New York time on the festival's end date
- **THEN** it is attached, though that moment is the next day in UTC

#### Scenario: Several festivals match
- **WHEN** a show matches two festivals
- **THEN** it attaches to the one that starts latest

#### Scenario: Several festivals start the same day
- **WHEN** a show matches two festivals with the same start date
- **THEN** it attaches to the one with the lower id

#### Scenario: No start time
- **WHEN** a show with no start time is saved
- **THEN** it has no festival

#### Scenario: Dates change
- **WHEN** an editor moves a festival's end date earlier so an automatically attached show falls outside it
- **THEN** that show is detached

#### Scenario: Show moves
- **WHEN** an automatically attached show's start is changed to a day outside the festival
- **THEN** it is detached when saved

#### Scenario: Unapproved show
- **WHEN** an unapproved show matches a festival
- **THEN** it is attached, but isn't listed on the festival's page until it is approved

### Requirement: Match words and town narrow the match
A festival's match words SHALL be its title unless an editor lists others (comma separated). A festival MAY name a town; when it does, the show's venue town SHALL also match it. A show matching several festivals SHALL attach to the one starting latest, then the lowest id. A show with no start time SHALL have no festival.

#### Scenario: Own match words
- **WHEN** a festival "Porchfest" lists the match words "porch fest, porchfest" and a show is titled "Porch Fest Sunday"
- **THEN** the show is attached on a festival day

### Requirement: Attachments are kept current
A show no festival matches SHALL stay unattached, and a previously automatic attachment that no longer matches SHALL be removed.

#### Scenario: Nothing matches
- **WHEN** a show matches no festival
- **THEN** it has no festival

### Requirement: Editors can override a show's festival
An editor SHALL be able to choose a festival for a show in the admin, and to mark a show as not part of any festival. A show set by an editor, either way, SHALL NOT be changed by automatic matching, a festival's edit or a re-fetch. Clearing the choice SHALL return the show to automatic matching. The admin's event list SHALL be filterable by festival.

#### Scenario: Editor attaches a show
- **WHEN** an editor picks a festival on a show that doesn't match it
- **THEN** the show is attached, recorded as set by an editor, and stays after the festival's dates are edited

#### Scenario: Editor detaches a show
- **WHEN** an editor marks a matching show as not part of any festival
- **THEN** it has no festival, and a later save of the show or the festival doesn't attach it

#### Scenario: Back to automatic
- **WHEN** an editor clears their choice on a show
- **THEN** the show is matched automatically on its next save

#### Scenario: Filter by festival
- **WHEN** an editor filters the event list by a festival
- **THEN** only that festival's shows are listed

### Requirement: Shows link to their festival
An attached show's event page and its row in the listing SHALL carry a link to the festival's page naming the festival. A show with no festival SHALL show no such link. When a show's festival changes, its stored row SHALL be re-rendered.

#### Scenario: Link on the event page
- **WHEN** a visitor opens the page of a show attached to "Porchfest"
- **THEN** the page links to the festival's page, naming it

#### Scenario: Row link follows changes
- **WHEN** an editor detaches a show from its festival
- **THEN** the show's row no longer has the link

#### Scenario: No festival
- **WHEN** a show has no festival
- **THEN** its page and row show no festival link

### Requirement: A command matches existing shows to a new festival
`match_festivals` SHALL run the automatic matching over all shows (or one festival's, with `--festival <slug>`), attaching and detaching only shows not set by an editor, and printing what it changed. `--dry-run` SHALL print the changes without saving them. It SHALL be a recorded job run.

#### Scenario: Dry run
- **WHEN** `match_festivals --dry-run` runs with matching shows unattached
- **THEN** it lists the shows it would attach and saves nothing

#### Scenario: Run
- **WHEN** `match_festivals` runs after a festival is created
- **THEN** matching past and upcoming shows are attached, editor-set shows are untouched, and a job run is recorded
