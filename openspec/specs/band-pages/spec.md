# band-pages Specification

## Purpose
TBD - created by archiving change add-band-pages. Update Purpose after archive.

## Requirements

### Requirement: Every band and artist has a public page
Each band SHALL have a page at `/bands/<slug>` and each artist at `/artists/<slug>`, where the slug is made from the name and is unique within its kind. The page SHALL show the act's name; a line with its kind, genres, origin (its home town and state, or else its MusicBrainz area) and formed year, each only when known; its upcoming shows; and the fields and bio below, each only when the act has it. A field with nothing in it SHALL NOT be drawn. An unknown slug SHALL answer 404.

#### Scenario: A band with everything
- **WHEN** a visitor opens the page of a band with a bio, members, links, a photo and two upcoming shows
- **THEN** the page shows its name, its kind, genre, origin and year, a next-show strip, its members, links, photo, bio and both shows

#### Scenario: A band with only a name and shows
- **WHEN** a visitor opens the page of a band with no bio, members, links or photo
- **THEN** the page shows its name, its shows and the invitation to send more, and no empty members, links, photo or bio fields

#### Scenario: Unknown band
- **WHEN** a visitor opens `/bands/no-such-band`
- **THEN** the site answers 404

### Requirement: The next show leads
The page SHALL show the act's next upcoming approved show directly under its name, with its date and time, venue and town, a link to the event, and how many more upcoming shows there are; and SHALL list all its upcoming approved shows in date order, each with the date, venue and town, linking to the event. An act with no upcoming shows SHALL say so in one line in place of the strip. Shows come from the act's event performer links, and only approved events count.

#### Scenario: Next show and the rest
- **WHEN** a band plays the District Music Hall in Norwalk on Oct 29 and 3S Artspace in Portsmouth on Nov 2
- **THEN** the strip shows Oct 29 at District Music Hall, Norwalk, CT and "1 more show", and the list shows both in date order

#### Scenario: No upcoming shows
- **WHEN** a band has only past events
- **THEN** the page says there are no upcoming shows listed, and shows no strip

#### Scenario: Unapproved events
- **WHEN** a band is linked to an unapproved event
- **THEN** that event isn't shown

### Requirement: Members and bands
A band's page SHALL list its members, current ones first and then former ones, each with their role and years when known, linked to their artist page, with their headshot when they have a freely licensed photo. An artist's page SHALL list the bands they're in, with their role and years when known, linked to each band's page.

#### Scenario: Current and former members
- **WHEN** a band has two members with no end year and six with one
- **THEN** the two are listed first, then the six as former members, each with their years

#### Scenario: An artist's bands
- **WHEN** a visitor opens the page of an artist who is a member of two bands
- **THEN** the page lists both bands, linked

### Requirement: Links
The page SHALL link to the act's website, Bandcamp page, Instagram and YouTube channel, each only when the act has it, opening on their own sites.

#### Scenario: Some links
- **WHEN** a band has a website and a Bandcamp page but no Instagram or YouTube
- **THEN** only the website and Bandcamp are linked

### Requirement: Photos only under a free licence, credited
The page SHALL show an act's photo only when it has a Wikimedia Commons file with a free licence (public domain, CC0, CC BY or CC BY-SA), loading Commons' thumbnail of it, and SHALL credit it beside the image with its author and licence, linking the file's Commons page and the licence. A member's headshot SHALL follow the same rule. The site SHALL NOT store the image itself.

#### Scenario: A credited photo
- **WHEN** a band's photo is "Bonerama2006.jpg" by a named author under CC BY-SA 3.0
- **THEN** the page shows the Commons thumbnail with "Photo: <author>, CC BY-SA 3.0", linked to the file and the licence

#### Scenario: No free photo
- **WHEN** a band has no Commons photo with a free licence
- **THEN** no photo field is drawn

### Requirement: The bio, credited
The page SHALL show the act's Wikipedia opening paragraph word for word, credited "From the Wikipedia article <title>, under CC BY-SA 4.0" with both linked; or, when it has none, its MusicBrainz disambiguation note; or no bio. Genres from MusicBrainz SHALL be credited to MusicBrainz.

#### Scenario: Wikipedia bio
- **WHEN** a band has a Wikipedia paragraph
- **THEN** it's shown with its credit and links

#### Scenario: Only a disambiguation note
- **WHEN** a band has no Wikipedia paragraph and the note "Boston indie rock band"
- **THEN** the note is shown as the bio, with no Wikipedia credit

### Requirement: Inviting the band to add more
A page missing a photo, a bio or links SHALL show one quiet line inviting the act to send them, as an email link to the site's contact address with the act's name and page in the subject.

#### Scenario: The invitation
- **WHEN** a band's page has no photo and no bio
- **THEN** it shows the line inviting the band to send a photo, bio and links, linking an email to the contact address

### Requirement: Events link to their acts
On the calendar, each name in an event's listing, in its title or its artists, that is one of its performers SHALL link to that performer's page, including a performer's name that starts a longer title ("Built to Spill Fall 2026 Tour"). Names that aren't performers, and a presenter's prefix ("AS220 Presents:"), SHALL stay plain text. When an event has performers, its own page (the venue's listing) SHALL be a small "info" link after the venue, and no name SHALL link to it; an event without performers SHALL keep its listing as before.

#### Scenario: A linked performer
- **WHEN** an event's Artists are "Pixies, Dana and Alden" and Pixies is a performer
- **THEN** "Pixies" links to `/bands/pixies` and "Dana and Alden" stays plain

#### Scenario: The headliner in the title
- **WHEN** an event titled "Axe Collector" has the Artists "Phantom Rider, Zipper, Anthropocene", and Axe Collector, Phantom Rider and Zipper are performers
- **THEN** all three names link to their pages, Anthropocene stays plain, and the venue's page is the "info" link after the venue

#### Scenario: No performers
- **WHEN** an event has no performers
- **THEN** its title links to its own page as before, with no "info" link

### Requirement: The page reads well on phones and to every visitor
The page SHALL fit a 390px-wide screen with no sideways scrolling and the next show directly after the name; images SHALL have text alternatives naming the act or member; links and the card's fields SHALL be readable at the site's contrast; and the page SHALL have a title and description naming the act.

#### Scenario: On a phone
- **WHEN** the page is opened 390px wide
- **THEN** the name, then the next show, are in the first screen, and nothing scrolls sideways
