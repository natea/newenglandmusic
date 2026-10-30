## ADDED Requirements

### Requirement: Photos and social links from Wikidata, Commons and MusicBrainz
For a matched record with a Wikidata ID, enrichment SHALL read the item's image (P18), Instagram username (P2003) and YouTube channel ID (P2397). For the image it SHALL fetch the file's licence and author from Wikimedia Commons and keep the file name, author, licence name and licence link only when the licence is free (public domain, CC0, CC BY or CC BY-SA); otherwise no photo. From MusicBrainz's links it SHALL also take an `instagram.com` link and a YouTube channel link. A record's Instagram and YouTube links SHALL be kept when an editor set them, and Wikidata's or MusicBrainz's otherwise. No image file SHALL be stored. Requests SHALL send the contact user agent and be paced.

#### Scenario: A free photo
- **WHEN** a band's Wikidata item has the image "Bonerama2006.jpg", which Commons lists under CC BY-SA 3.0 by a named author
- **THEN** the band keeps the file name, the author, "CC BY-SA 3.0" and its licence link

#### Scenario: A file without a free licence
- **WHEN** Commons gives no free licence for the file
- **THEN** the band keeps no photo

#### Scenario: Social links
- **WHEN** MusicBrainz lists `https://www.instagram.com/speedyortiz/` and Wikidata a YouTube channel ID
- **THEN** the band keeps both links

#### Scenario: An editor's link stays
- **WHEN** an editor set a band's Instagram link and enrichment finds another
- **THEN** the editor's link stays
