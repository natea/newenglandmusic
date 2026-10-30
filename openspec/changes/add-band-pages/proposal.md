## Why

The site now has artist and band records, filled from MusicBrainz and Wikipedia and linked to their events, but nobody outside the admin can see them. A fan who spots an unfamiliar name on the calendar has nowhere to find out who the band is, and a band has no page to point people to. PRODUCT.md serves fans and musicians equally; a page per act serves both: when they play next in the Northeast, and who they are.

## What Changes

- **A public page for every band and artist,** at `/bands/<slug>` and `/artists/<slug>`, designed as a record-store index card in the site's existing look (the direction chosen on 2026-10-29, in `.impeccable/surfaces/core-templates-core-band-html.md`):
  - a purple tab over an off-white card, the act's name large, then a line with its kind, genre, origin and formed year;
  - a lavender **next show** strip right under the name (date, venue, town, link to the event, and how many more), first on phones too;
  - fields: members (with roles and years, current then former, linked to their own pages, with headshots when a free one exists), links (website, Bandcamp, Instagram, YouTube), and the photo when a freely licensed one exists;
  - the bio on ruled lines: Wikipedia's opening paragraph with its credit, or MusicBrainz's disambiguation note;
  - the full list of upcoming shows, from the event performer links;
  - an artist's page lists the bands they're in instead of members.
- **Only what exists is drawn.** A local band with just a name and a few shows gets a short card with no empty fields, plus a quiet line inviting the band to send a photo, bio and links (by email to the site's contact address).
- **Photos and headshots from Wikimedia Commons, only under a free licence.** For an act with a Wikidata ID, the enrichment reads its Wikidata image (P18), then the file's licence and author from Commons. Only a file with a free licence is kept (public domain, CC0, CC BY, CC BY-SA), as its file name, author, licence and licence link, never the image itself. The page shows Commons' own thumbnail with the credit under it ("Photo: <author>, <licence>"). No photo means no photo field: nothing is guessed or scraped.
- **Instagram and YouTube links.** From MusicBrainz's links (an `instagram.com` "social network" link; a YouTube channel link) and Wikidata (Instagram username P2003, YouTube channel P2397). An editor's link always wins.
- **Events link to their acts.** On the calendar, a performer's name in an event's listing links to its page, so the pages can be found.

### Not in this change

- Play buttons on the band page (the calendar keeps them).
- A form for bands to edit their own page; the invitation is an email for now.
- Past shows, setlists, releases, or anything from Last.fm (whose terms forbid showing its data) or Bandcamp (links only).

## Capabilities

### New Capabilities
- `band-pages`: the public band and artist pages, their content, sparse and credited states, and the links to them from events.

### Modified Capabilities
- `artist-records`: enrichment also keeps a freely licensed photo's credit details, and Instagram and YouTube links.

## Impact

- **Code:**
  - `MusicAct` gains `slug`, `instagram_url`, `youtube_url`, and `photo_file`, `photo_author`, `photo_license`, `photo_license_url`, with a migration;
  - `core/wikipedia.py` gains the Wikidata image and Commons licence lookups;
  - `enrich_artists_from_musicbrainz` stores them;
  - new views, URLs and templates (`core/templates/core/band.html`, with an artist variant) and their stylesheet;
  - the event template links performers;
  - the admin shows and edits the new fields.
- **Services:** Wikidata and Wikimedia Commons, free and keyless, with the contact user agent; two more requests per record with a Wikidata image. The page loads Commons thumbnails from `upload.wikimedia.org`, which Wikimedia allows.
- **Licences:** each photo is credited with its author and licence as Commons requires; Wikipedia text and MusicBrainz genres keep their credits.
- **Depends on** `add-artists-from-events` for the event performer links.
- **Site still unshared:** the pages go live with the rest of the site; nothing changes about when it's shared.
