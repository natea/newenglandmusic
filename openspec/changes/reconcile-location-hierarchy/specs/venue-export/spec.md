# Spec Delta

## ADDED Requirements

### Requirement: The file shows where the site places each venue
Each row SHALL include, after the venue's own town and county, the venue's matched town, its listed neighborhood, its sub-region and its region, by their display names, and whether an editor set the placement. A venue with no matched town SHALL have these cells blank.

#### Scenario: A placed venue
- **WHEN** a venue whose town text is "Florence" is matched to Northampton, in Pioneer Valley, in Western Massachusetts
- **THEN** its row has the town "Florence", the matched town "Northampton", the sub-region "Pioneer Valley" and the region "Western Massachusetts"

#### Scenario: An unplaced venue
- **WHEN** a venue has no matched town
- **THEN** its matched town, listed neighborhood, sub-region and region cells are blank
