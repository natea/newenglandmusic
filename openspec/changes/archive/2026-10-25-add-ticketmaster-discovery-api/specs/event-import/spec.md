# Spec Delta

## MODIFIED Requirements

### Requirement: Venues are fetched according to the report
The import SHALL read the event-source report and fetch each selected venue from its best source, except that venues linked to Ticketmaster are fetched as `ticketmaster-event-import` describes. By default it SHALL fetch a small pilot per source. It SHALL fetch every usable venue with `--all`, or named venues with `--sheet-ids`. It SHALL fail clearly when the report is missing.

#### Scenario: Missing report
- **WHEN** the import runs and the report file doesn't exist
- **THEN** it exits with an error telling the user to run the source check first

#### Scenario: Fetch everything
- **WHEN** the import runs with `--all`
- **THEN** every venue whose best source is ical, json-ld, ticketing or ai-extraction is fetched, and venues with other classifications are not, unless they are linked to Ticketmaster

#### Scenario: Linked venue with a scrapeable source
- **WHEN** a venue linked to Ticketmaster has best source ical, ticketing or ai-extraction
- **THEN** it is fetched from the Ticketmaster Discovery API only, not also from its report source
