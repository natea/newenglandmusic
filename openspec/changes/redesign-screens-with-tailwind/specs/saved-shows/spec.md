# Spec Delta

## MODIFIED Requirements

### Requirement: The header shows a Saved shows link with a count
Every page's header SHALL have a "Saved" link to `/saved`. When JavaScript is on and the visitor has saved shows, the link SHALL show their number in a badge beside it, announced to screen readers with the link as "Saved, 3 shows", and SHALL update as shows are saved and unsaved. The count SHALL be of the IDs in the cookie, so it can briefly include shows the Saved shows page will drop.

#### Scenario: Count shown
- **WHEN** a visitor has saved three shows
- **THEN** the header's "Saved" link shows a badge reading "3"

#### Scenario: Count updates
- **WHEN** the visitor saves a fourth show
- **THEN** the badge reads "4" without a reload

#### Scenario: Nothing saved
- **WHEN** the visitor has saved nothing
- **THEN** the header link reads "Saved", with no badge
