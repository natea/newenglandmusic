# Spec Delta

## MODIFIED Requirements

### Requirement: Nothing is deleted, and the admin opens on New England
No venue or event SHALL be deleted. The admin's event list, its all-events review queue and its venue list SHALL by default leave out events and venues whose venue's state is set to a state outside New England, and SHALL offer an "All areas" choice that shows every one. A venue with no state, and an event with no venue, SHALL stay in the default list, as an editor needs to see them. A State, Region or Sub-region filter chosen in the admin SHALL show that area's events or venues wherever it is, without the default narrowing them. Only the State filter reaches outside New England: regions and sub-regions exist for New England alone.

#### Scenario: Admin opens on New England
- **WHEN** an editor opens the all-events review queue with no filter chosen
- **THEN** only events at New England venues are listed, and an unapproved event at a New York venue isn't

#### Scenario: No state, or no venue
- **WHEN** a venue has no state, and an event was submitted with no venue
- **THEN** both are in the admin's default lists

#### Scenario: All areas
- **WHEN** the editor chooses "All areas"
- **THEN** events at venues everywhere are listed, the New York one included

#### Scenario: A chosen state outside New England
- **WHEN** the editor chooses the State filter "New York" in the venue list
- **THEN** New York's venues are listed

#### Scenario: Nothing deleted
- **WHEN** the scope applies
- **THEN** no event or venue was deleted

#### Scenario: Artist matching unchanged
- **WHEN** an artist is named only by an approved event at a New York venue and `match_spotify_artists` runs
- **THEN** the artist is still matched, as before

#### Scenario: Removing the old areas deletes no venue
- **WHEN** the areas outside New England are removed from the admin's filters
- **THEN** every venue and event outside New England is still in the database
