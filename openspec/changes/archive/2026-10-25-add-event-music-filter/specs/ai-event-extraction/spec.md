# Spec Delta

## ADDED Requirements

### Requirement: Extracted events carry their kind
Each AI-extracted event SHALL include its kind (as defined by `event-music-filter`), set in the same extraction request, so no separate labelling request is needed for it. A kind outside the allowed values SHALL leave the event unlabelled.

#### Scenario: Comedy on a venue page
- **WHEN** a venue page lists "IMPROV COMEDY: an evening of laughs" and "Samantha Fish w/ Sgt. Splendor"
- **THEN** the extracted events are labelled `comedy` and `live_music`, and no labelling request is made for them

#### Scenario: Unknown kind returned
- **WHEN** the model returns a kind that isn't one of the allowed values
- **THEN** the event is saved unlabelled
