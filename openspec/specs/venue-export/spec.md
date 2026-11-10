# venue-export Specification

## Purpose
Let the site's editors and admins download the venue list from the admin as a spreadsheet file, with everything the site may share about each venue, so they can analyse it outside the site.

## Requirements

### Requirement: Staff can download the venue list as CSV

The admin's venue list SHALL have an "Export to CSV" button. It SHALL download a UTF-8 CSV file with one header row and one row per venue, ordered as the list is, with a filename that includes the date. The file SHALL hold the venues the list is showing: all venues when no search or filter is applied, otherwise only those matching the current search and filters, whatever the page size.

#### Scenario: Export everything

- **WHEN** a signed-in admin clicks the button on the unfiltered venue list, which has 3 venues
- **THEN** the response is a CSV download with a header row and 3 venue rows

#### Scenario: Export a filtered list

- **WHEN** an admin filters the list to active venues in Massachusetts, which are 2 of 3 venues, and clicks the button
- **THEN** the file has a header row and only those 2 venues

#### Scenario: Export a searched list

- **WHEN** an admin searches the list for "paradise" and clicks the button
- **THEN** the file has only the venues the search finds

#### Scenario: More venues than a page

- **WHEN** the list shows 100 venues per page and 250 venues match
- **THEN** the file has all 250 venue rows

#### Scenario: Opens in Excel

- **WHEN** the file is opened in Excel
- **THEN** a venue named "Café Lena" shows its accented letter correctly, because the file starts with a byte order mark

### Requirement: The file holds every shareable detail of a venue

Each row SHALL include every detail the sheet holds about the venue (sheet ID, name, active flag, type, size, state, town, county, the sheet's latitude and longitude, genres joined with semicolons, notes, booking, access and safety details), its neighborhood and the neighborhood's source, and its Ticketmaster, Eventbrite and SeatGeek IDs and ticket page link. Yes/no flags SHALL read "yes", "no" or blank when unknown.

#### Scenario: Sheet fields in the row

- **WHEN** a venue has a name, town, genres "Funk" and "Jazz", and `open_booking` true
- **THEN** its row has that name and town, the genres "Funk; Jazz" and "yes" for open booking

#### Scenario: Unknown flag

- **WHEN** a venue's open-booking flag is unknown
- **THEN** its open-booking cell is blank, not "no"

### Requirement: The file includes lookup and event-source details

Each row SHALL also include the Google place ID, the lookup status and its review reasons, and the saved result of the venue's last event-source check (best source, events page, calendar feed link, ticketing platforms, when checked), left blank when there is none.

#### Scenario: Event source included

- **WHEN** a venue's last event-source check found an iCal feed
- **THEN** its row has the best source "ical" and the feed link, and a venue never checked has those cells blank

### Requirement: Google's coordinates are never exported

The file SHALL NOT contain a venue's Google place latitude or longitude, the distance from them, or when they were fetched, under any column, whatever the venue's lookup status. The sheet's own latitude and longitude SHALL still be included.

#### Scenario: Confident match

- **WHEN** a venue has a confident Google match with place coordinates and a place ID
- **THEN** its row has the place ID and the status "confident", the sheet's coordinates, and no Google coordinate, distance or fetch time anywhere in the file

### Requirement: Only staff who may view venues can export

The export SHALL be available only to a signed-in staff user who has permission to view venues. Anyone else, including visitors who are signed out and staff without that permission, SHALL be refused, and no venue data SHALL be sent. The button SHALL not be shown to them.

#### Scenario: Signed-out visitor

- **WHEN** a visitor who isn't signed in requests the export address
- **THEN** they are sent to the admin login page and the response has no venue data

#### Scenario: Staff without permission

- **WHEN** a staff user without permission to view venues requests the export
- **THEN** the response is a refusal and has no venue data

#### Scenario: Member of the admin group

- **WHEN** a staff user in the "admin" group clicks the button
- **THEN** the file downloads

### Requirement: Cells can't run as formulas

A text cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return SHALL be written with a leading apostrophe, so a spreadsheet shows it as text rather than running it. Text with commas, quotes or line breaks SHALL be quoted so each venue stays on one row.

#### Scenario: Formula-like note

- **WHEN** a venue's booking notes are `=HYPERLINK("http://example.com")`
- **THEN** the cell reads `'=HYPERLINK("http://example.com")` in the file

#### Scenario: Commas and line breaks

- **WHEN** a venue's notes are "Call ahead, ask for Sam" over two lines
- **THEN** the file still reads back with one row for that venue and the full notes in one cell
