# artist-link-hubs Specification

## Purpose
Read the link-hub pages an act already points to, such as a Linktree, where the hub allows it, to fill the act's empty Bandcamp, Instagram, YouTube and website fields, and show editors what disagrees.

## Requirements

### Requirement: A record keeps its link-hub address
A band or artist SHALL be able to have one link-hub address: a page on a supported hub (see the design). It SHALL come from the record's website when that is on a supported hub, from a MusicBrainz link on one (taken during enrichment), or from an editor in the admin. An editor's address SHALL NOT be replaced by another source.

#### Scenario: Hub address as the website
- **WHEN** an artist's website is `https://linktr.ee/sunnydaze`
- **THEN** the command copies that address to the artist's link-hub address (stored, marked with the website's source) before reading, and leaves the website unchanged

#### Scenario: Hub address from MusicBrainz
- **WHEN** enrichment finds a MusicBrainz link to `https://beacons.ai/krillband` on a band with no hub address
- **THEN** the band's hub address is that address, marked as MusicBrainz's

#### Scenario: Not a page on a hub
- **WHEN** an editor enters `https://linktr.ee/` or `https://example.com/links` as a hub address
- **THEN** the admin rejects it and saves nothing

#### Scenario: Editor's address kept
- **WHEN** an editor set a hub address and MusicBrainz lists a different one
- **THEN** the editor's address stays

### Requirement: Only real hub pages are accepted
An address SHALL be stored as `https`, and one that isn't a page on a supported hub (the hub's home page, or another site) SHALL be rejected. A website that is a hub address SHALL be kept, never replaced from the hub, and SHALL NOT count as the act's own website when links are compared: a real website on the hub is saved as a finding.

#### Scenario: A hub address in the website field
- **WHEN** an artist's website is a hub address and its hub links `https://sunnydaze.com` under the label "Website"
- **THEN** the artist's website stays the hub address, with its `field_sources` entry unchanged, and a finding on the website shows both addresses

#### Scenario: A hub address too long for its field
- **WHEN** a hub's Instagram link is longer than the Instagram field allows
- **THEN** it is not used, no finding is saved, and the record's update doesn't fail

### Requirement: Reading a hub page
`read_artist_link_hubs` SHALL read the hub page of each record with an address that was never read or was read over seven days ago (`--refresh` reads all; `--limit` caps the run; `--dry-run` saves nothing). Before choosing them it SHALL give a record whose website is a hub address that address as its hub address.

#### Scenario: A readable hub
- **WHEN** a record's Linktree page, replayed from a fixture, links to a Bandcamp page, an Instagram profile and a YouTube channel
- **THEN** the record's status is "read" with the time, and the Bandcamp, Instagram and YouTube links the record lacked are filled

#### Scenario: Robots forbids it
- **WHEN** the hub's robots.txt disallows the page for the site's user agent
- **THEN** the page is not requested, and the status is "blocked"

#### Scenario: A deleted hub page
- **WHEN** the hub answers 404 for the address
- **THEN** the status is "gone", and the links already on the record are kept

#### Scenario: A hub that can't be read
- **WHEN** a page loads but its links are built by script and none are in the page
- **THEN** the status is "unreadable", the address stays on the record, and the run goes on

#### Scenario: Recently read records are skipped
- **WHEN** a record was read three days ago and the command runs without `--refresh`
- **THEN** its page is not requested

#### Scenario: One failure doesn't stop the run
- **WHEN** one record's page times out
- **THEN** its status is "failed", the others are read, and the run reports the failure

### Requirement: Reading a hub page politely
The command SHALL obey robots.txt, send the site's honest user agent (the one the event checks send, which contains `venue-db-event-check/1.0`), make at most one request a second, run no JavaScript, and follow no redirect off the hub's host.

#### Scenario: A redirect off the hub
- **WHEN** a hub page redirects to another host
- **THEN** the redirect is not followed and the status is "failed"

### Requirement: The result of a read is recorded
Each read SHALL set the record's status: "read" (with the time), "empty" (no usable links), "unreadable" (the hub builds its links in the browser), "blocked" (robots.txt, or HTTP 403, 406 or 429), "gone" (HTTP 404 or 410) or "failed" (any other error, which SHALL NOT stop the run). The run is a recorded job and SHALL list the records that were blocked, gone or failed.

#### Scenario: A page with no links
- **WHEN** a hub page loads with no links on it
- **THEN** the status is "empty"

### Requirement: Which links are recognised
By address, the command SHALL recognise a Bandcamp URL (`https` on `bandcamp.com` or a subdomain), an Instagram URL (an `https` profile on `instagram.com`) and a YouTube URL (an `https` channel, handle or user page on `youtube.com`, not a video or playlist). It SHALL recognise a website only from a link whose label on the hub says "website", "site", "homepage" or "official" and whose address isn't a social, streaming, ticketing or hub site.

#### Scenario: A link on another site
- **WHEN** a hub's unlabeled link goes to `https://example.com/shop`
- **THEN** it is not used as the website

### Requirement: Filling in missing links
When the page gives exactly one recognised link for an empty field, the command SHALL fill it and mark it "link hub" in `field_sources`. When it gives several for one field, it SHALL fill nothing and save a finding. It SHALL NOT change a field set by an editor, the import, MusicBrainz or Wikidata, nor request any page it took a link from.

#### Scenario: Filling an empty field
- **WHEN** a band has no Instagram link and its hub links `https://www.instagram.com/krill.band/`
- **THEN** the band's Instagram link is that address, marked "link hub"

#### Scenario: Several candidates
- **WHEN** a hub lists two Instagram profiles and the record has none
- **THEN** the record's Instagram link stays empty and a finding lists both

#### Scenario: A video is not a channel
- **WHEN** a hub's only YouTube link is `https://www.youtube.com/watch?v=abc123` and the record has no YouTube link
- **THEN** the record's YouTube link stays empty

#### Scenario: The hub's own label names the website
- **WHEN** a hub link labeled "Official website" goes to `https://krillband.com`, and the record has no website
- **THEN** the website is `https://krillband.com`

#### Scenario: Protected values stay
- **WHEN** the record's website was set by an editor and the hub's website link differs
- **THEN** the website is unchanged, and the difference is saved as a finding

#### Scenario: Not a Bandcamp address
- **WHEN** a hub's "Bandcamp" link goes to `https://example.com/music`
- **THEN** it is not used

### Requirement: Hub-filled links are the hub's to update
A link filled by the hub is the only value the command may replace: it SHALL be replaced when a later read gives a different single link, and one gone from the page SHALL be kept. A re-run of enrichment SHALL leave a hub-filled link alone unless MusicBrainz or Wikidata has a value for the field, which then replaces it.

#### Scenario: Enrichment keeps a hub fill
- **WHEN** a band's Instagram link was filled from its hub and enrichment runs again with MusicBrainz and Wikidata having no Instagram link
- **THEN** the Instagram link stays, still marked "link hub"

#### Scenario: A hub fill is replaced by MusicBrainz
- **WHEN** a band's Instagram link was filled from its hub and enrichment finds a different one on MusicBrainz
- **THEN** the link is MusicBrainz's, marked as such

#### Scenario: A changed hub replaces its own fill
- **WHEN** a band's Instagram link was filled from its hub and a later read gives a different single Instagram link
- **THEN** the link is the new one, still marked "link hub", and no finding is saved

### Requirement: Differences are flagged, not applied
When a hub link is for a field the record already has, and the two differ, the command SHALL save a finding (field, the record's value, the hub's value, when seen) and SHALL NOT change the field. Two addresses SHALL count as the same when their hosts (ignoring `www.` and `m.`) and paths (ignoring case and a trailing slash) match, whatever the query.

#### Scenario: The same address written differently
- **WHEN** the record has `https://instagram.com/krill.band` and the hub links `https://www.instagram.com/Krill.Band/?hl=en`
- **THEN** no finding is saved

### Requirement: Findings are kept up to date
A finding SHALL be replaced when a later read sees a different hub value for the field, and removed when the hub and the record agree or the hub no longer links the field. A finding an editor dismissed SHALL NOT come back for the same hub value.

#### Scenario: A conflicting YouTube link
- **WHEN** a band's YouTube link is `https://www.youtube.com/@krill` and its hub links `https://www.youtube.com/channel/UC123`
- **THEN** the YouTube link is unchanged, and a finding shows both addresses

#### Scenario: A finding goes away
- **WHEN** an editor changes the record's link to the hub's value, and the next read runs
- **THEN** the finding is removed

#### Scenario: A dismissed finding
- **WHEN** an editor dismisses a finding and the next read sees the same hub value
- **THEN** no finding is saved

### Requirement: Editors review the findings
The admin SHALL show a record's hub address, status, time of the last read and findings, let an editor set or clear the address, and list the records with open findings (a filter, and a column with their number). For each finding an editor SHALL be able to accept it, which sets the field to the hub's value and marks it as the editor's, or dismiss it. The admin SHALL show the same for artists and bands.

#### Scenario: Accepting a finding
- **WHEN** an editor accepts a finding for the YouTube link
- **THEN** the record's YouTube link is the hub's value, marked as the editor's, and the finding is gone

#### Scenario: Records with findings
- **WHEN** an editor filters the list by "has link-hub findings"
- **THEN** only records with at least one open finding are listed

### Requirement: Supported hubs
The site SHALL read the hubs listed in one place in the code, each with the hosts that identify it and how its page is read; the list is settled by checking each live page (a task of the change) and recorded in the design. Linktree SHALL be supported, and the tests use Linktree and one other host marked address-only. A host SHALL be added only after its page has been checked to give its links without running JavaScript, or SHALL be listed as address-only.

#### Scenario: Address-only hub
- **WHEN** a record's address is on a hub listed as address-only
- **THEN** the address is kept, the page is not requested, and the status is "unreadable"

### Requirement: Problems are recorded per act
The run's list of problem records SHALL name each blocked, gone or failed act with its kind (artist or band), in the same list the venue jobs use, and the job-run page SHALL show it.

#### Scenario: A blocked act in the job run
- **WHEN** a record's hub is blocked during a run
- **THEN** the run's problems list names the act and "blocked", and the job-run page in the admin shows it
