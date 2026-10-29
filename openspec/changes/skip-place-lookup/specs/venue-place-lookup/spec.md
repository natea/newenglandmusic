## ADDED Requirements

### Requirement: Admins can keep a venue from being looked up
The venue admin SHALL offer an action to mark the selected venues as not to be looked up, for venues with no single place, such as festivals spread across a town. It SHALL remove any matched place (its place ID, coordinates, fetch time, review reasons and distance), set the lookup status to "Not looked up (no single place)", and re-render the stored HTML of the venues' upcoming events. Such a venue SHALL use the sheet's coordinates. No lookup SHALL search for it: not a plain run, nor one with `--refresh`, `--review` or `--refresh-stale`, including when it's named with `--sheet-ids`. Clearing its lookup SHALL make it a venue the next plain run searches for again. The lookup-status filter SHALL include the new status.

#### Scenario: Marking a festival
- **WHEN** an admin selects "Porchfest" in Somerville, a venue needing review matched to a park, and chooses "Don't look up on Google"
- **THEN** its place ID, coordinates, reasons and distance are removed, its status is "Not looked up (no single place)", and its events' map pins use the sheet's coordinates

#### Scenario: The daily lookup skips it
- **WHEN** `lookup_venue_places` runs, plain or with `--refresh`, `--review` or `--refresh-stale`
- **THEN** it makes no request for a venue marked not to be looked up, and doesn't list it in its report

#### Scenario: Named explicitly
- **WHEN** `lookup_venue_places --refresh --sheet-ids` names a venue marked not to be looked up
- **THEN** it's still skipped

#### Scenario: Undoing it
- **WHEN** an admin clears the lookup of a venue marked not to be looked up
- **THEN** its status is empty, and the next plain run searches for it

#### Scenario: Filtering
- **WHEN** an admin filters the venue list by the lookup status "Not looked up (no single place)"
- **THEN** only the venues marked that way are listed
