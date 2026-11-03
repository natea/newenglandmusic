# Spec Delta

## Purpose

Tell visitors who makes the site, why, and what it can do, and invite them to help by suggesting missing venues, bands and artists, or other ideas.

## ADDED Requirements

### Requirement: The site has an About page

The site SHALL have a public page at `/about` that introduces Nate, Sooz and Mark as the people behind the site and explains why the site was made. It SHALL need no login and no JavaScript to read.

#### Scenario: Page loads

- **WHEN** a visitor opens `/about`
- **THEN** the page answers successfully and names Nate, Sooz and Mark, and has a section on why the site exists

#### Scenario: Page has its own title

- **WHEN** a visitor opens `/about`
- **THEN** the page's title and heading say it is the About page

### Requirement: The page describes what the site can do

The About page SHALL describe the site's features that exist today, and each description SHALL link to the page where the feature is used. The features are the venue and show listings, the map, saved shows, searching venues and acts, band and artist pages, music previews, distance from a place the visitor names, and calendar feeds.

#### Scenario: Features link to their pages

- **WHEN** a visitor opens `/about`
- **THEN** the page links to the home page listing, the saved shows page, the bands and artists index and the calendar feed

### Requirement: The page invites contributions

The About page SHALL invite visitors to suggest venues, bands or artists that are missing, and to share any other idea. When the site has a contact email configured, the page SHALL offer a link that opens an email to it, and SHALL link to the event submission form for adding a show. When no contact email is configured, the page SHALL still load, SHALL show the invitation, and SHALL NOT show an empty or broken email link.

#### Scenario: Email link with a contact email

- **WHEN** a contact email is configured and a visitor opens `/about`
- **THEN** the page has a link to that address, and a link to the event submission form

#### Scenario: No contact email

- **WHEN** no contact email is configured and a visitor opens `/about`
- **THEN** the page answers successfully, shows the invitation, and has no email link

### Requirement: The About page is easy to find

Every page SHALL link to the About page from its footer, beside the Privacy link. The sitemap SHALL list the About page.

#### Scenario: Footer link

- **WHEN** a visitor opens the home page, the saved shows page, the event submission page or the privacy page
- **THEN** the footer on each has a link to `/about`

#### Scenario: Sitemap

- **WHEN** a search engine fetches the sitemap
- **THEN** it lists the address of the About page
