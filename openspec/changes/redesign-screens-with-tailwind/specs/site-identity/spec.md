# Spec Delta

## MODIFIED Requirements

### Requirement: The masthead carries a tagline

The footer SHALL show a tagline from `SITE_TAGLINE`, which defaults to "Live music across New England", beside the site's name. The header SHALL show the name alone. A blank or whitespace-only tagline SHALL show nothing.

#### Scenario: The default tagline

- **WHEN** a visitor opens any page with `SITE_TAGLINE` unset
- **THEN** the footer shows "Live music across New England" beside "StageHopper", and the header shows "StageHopper" alone

#### Scenario: No tagline

- **WHEN** `SITE_TAGLINE` is set to a single space
- **THEN** the footer shows the name alone
