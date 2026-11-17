## MODIFIED Requirements

### Requirement: Bandcamp only as a link
The site SHALL request nothing from Bandcamp except, in `find_bandcamp_embeds` (see `bandcamp-embed`), an act's own Bandcamp page and Bandcamp's player for a release on it, to read the numeric ID of a release the embedded player can play. It SHALL NOT scrape anything else from Bandcamp, use a proxy or scraping service, or request Bandcamp for any other reason, and enrichment, the imports and the link-hub reader SHALL request nothing from it. A record's Bandcamp URL SHALL come only from an editor, the import, MusicBrainz's links, or the record's link hub (see `artist-link-hubs`), and SHALL be accepted only when it's an `https` URL on `bandcamp.com` or a subdomain of it.

#### Scenario: A Bandcamp link from MusicBrainz
- **WHEN** MusicBrainz lists a band's Bandcamp page
- **THEN** the band stores that URL, and enrichment makes no request to Bandcamp

#### Scenario: Not a Bandcamp URL
- **WHEN** an import row's `Bandcamp` is "https://example.com/krill"
- **THEN** the row's Bandcamp URL is reported as invalid and not saved, and the rest of the row is imported

#### Scenario: The import asks Bandcamp for nothing
- **WHEN** an import row gives a valid Bandcamp URL
- **THEN** the URL is stored and no request is made to Bandcamp; the player lookup reads it later

## ADDED Requirements

### Requirement: Records keep a Bandcamp player
Artist and band records SHALL keep the Bandcamp player fields defined in `bandcamp-embed`. They SHALL be left alone by enrichment, the imports and clearing a MusicBrainz match, and a player an editor set SHALL be marked "editor" in `field_sources`.

#### Scenario: Clearing a match
- **WHEN** an admin clears a band's MusicBrainz match
- **THEN** its Bandcamp player and status stay

#### Scenario: Import leaves the player
- **WHEN** an import row updates a band that has a found player
- **THEN** the player's kind, ID, status and time are unchanged
