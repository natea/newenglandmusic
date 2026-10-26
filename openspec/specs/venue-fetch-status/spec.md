# venue-fetch-status Specification

## Purpose
Make problems with fetching a venue's events easy to see, on the run that hit them and on the venue itself, so an admin can tell which venues need attention without reading a fetch's whole report.

## Requirements

### Requirement: A fetch's problems are kept per venue

When `fetch_events` runs, the problems it meets for each venue SHALL be kept with that venue: pages that failed to load, Ticketmaster API errors and AI extraction failures. Informational notes SHALL NOT count as problems, for example a truncated page, events hidden as not music, or events left unlabelled.

#### Scenario: Failed page and informational note

- **WHEN** a fetch fails to load one page for a venue, and also leaves one of its events unlabelled
- **THEN** that venue has one problem, the failed page with its URL and error, and the unlabelled note is not a problem

### Requirement: The job run lists the venues with problems

A fetch's job run SHALL keep the list of venues that had problems, each with its sheet ID, name and problems. The job run's admin page SHALL show this list above the text report, in red, with each venue linking to its admin page. When there are none it SHALL say so. The job run list SHALL show each run's number of venues with problems, in red when it's more than zero.

#### Scenario: Run with problems

- **WHEN** a fetch has problems at 2 venues
- **THEN** its job run page lists both venues above the report, each with its problems and a link to the venue, and the job run list shows 2 in red

#### Scenario: Run without problems

- **WHEN** a fetch has no problems
- **THEN** its job run page says there were no problems, and the list shows 0

### Requirement: Each venue records its latest fetch

Each time a fetch that isn't a dry run fetches a venue, the venue's fetch status SHALL be replaced with that fetch's outcome:
- when it was fetched
- the source used (iCal, JSON-LD, ticketing, AI or Ticketmaster)
- how many events were found, and how many were upcoming
- its problems
- the job run it came from

A dry run SHALL NOT change any venue's fetch status. A venue the fetch didn't select SHALL keep its previous status.

#### Scenario: Fetched venue

- **WHEN** a fetch finds 12 events, 9 of them upcoming, for a venue, with no problems
- **THEN** the venue's fetch status shows that time, its source, 12 found, 9 upcoming, no problems, and the job run

#### Scenario: Dry run

- **WHEN** a dry run fetches a venue
- **THEN** the venue's fetch status is unchanged

### Requirement: The venue admin shows fetch status

The venue admin list SHALL show each venue's fetch status as one of these:
- **problems:** the latest fetch had at least one problem
- **nothing found:** no problems, but no upcoming events
- **OK:** upcoming events found and no problems
- **never fetched**

Problems SHALL stand out in red. The list SHALL be filterable by these four states. Each venue's admin page SHALL show its latest fetch's details and problems, with a link to the job run.

#### Scenario: Filter to problem venues

- **WHEN** an admin filters the venue list to problems
- **THEN** only venues whose latest fetch had problems are listed, each marked in red

#### Scenario: Venue page

- **WHEN** an admin opens a venue whose latest fetch had a failed page
- **THEN** its page shows the fetch time, source, counts, the failed page with its error, and a link to the job run

#### Scenario: Never fetched

- **WHEN** an admin views a venue that has never been fetched
- **THEN** the list shows it as never fetched
