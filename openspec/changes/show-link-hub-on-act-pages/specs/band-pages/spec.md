## ADDED Requirements

### Requirement: The link hub is shown prominently
When an act has a link-hub address (`link_hub_url`, or a supported hub address in the website field), its page SHALL show one link to it near the top of the card, above the members, bands and links, labelled "All links on <hub name>" (the name from the supported hubs). Placement follows the chosen screen design. An act with no hub address SHALL have no such link and its page SHALL be unchanged.

#### Scenario: An act on Linktree
- **WHEN** a visitor opens the page of a band whose link hub is `https://linktr.ee/bonerama`
- **THEN** the page shows "All links on Linktree" linking there, near the top, before the members and links

#### Scenario: Another hub
- **WHEN** an artist's link hub is `https://solo.to/dana`
- **THEN** the link reads "All links on Solo.to"

#### Scenario: No link hub
- **WHEN** a band has no link-hub address
- **THEN** the page has no "All links" link and looks as it did before

### Requirement: The hub link stands apart from the other links
The hub link SHALL open the hub on its own site (new tab, `rel="noopener"`), and SHALL NOT also appear in the Links row, including when the hub address is stored in the website field. When the address is not on a supported hub, the label SHALL be "All links".

#### Scenario: Not repeated among the links
- **WHEN** a band has a website, a Bandcamp page and a link hub
- **THEN** the Links row shows the website and Bandcamp only, and the hub appears once, as the labelled link

#### Scenario: Hub address only in the website field
- **WHEN** a band's website is `https://linktr.ee/bonerama` and it has no separate link-hub address
- **THEN** the page shows "All links on Linktree" linking there, and the Links row has no Website entry for it

#### Scenario: An address on no supported hub
- **WHEN** an editor has entered a link-hub address that is on none of the supported hubs
- **THEN** the link reads "All links" and still opens that address

## MODIFIED Requirements

### Requirement: Inviting the band to add more
A page missing a photo, a bio or links SHALL show one quiet line inviting the act to send them, as an email link to the site's contact address with the act's name and page in the subject. An act's link-hub address SHALL count as links: a page with a hub address and none of the Website, Bandcamp, Instagram or YouTube links SHALL NOT be invited to send links. When the hub is the act's only links, the line and the email's body SHALL ask only for what is missing, without "links"; in every other case their wording is unchanged.

#### Scenario: The invitation
- **WHEN** a band's page has no photo and no bio
- **THEN** it shows the line inviting the band to send a photo, bio and links, linking an email to the contact address

#### Scenario: Only a link hub
- **WHEN** a band has a photo, a bio and a link-hub address but no Website, Bandcamp, Instagram or YouTube link
- **THEN** its page shows the hub link and no invitation

#### Scenario: A hub with other links and a missing photo
- **WHEN** a band has a website, a link-hub address and a bio but no photo
- **THEN** the invitation wording is the same as it would be without the hub

#### Scenario: A hub and a missing photo
- **WHEN** a band has a link-hub address and a bio but no photo
- **THEN** the visible line and the email body ask for a photo and not for links
