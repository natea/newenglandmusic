## Why

The site knows venues as records but artists only as names on events, held per name for the Spotify, Apple Music and YouTube links. There's no record of a band, who's in it, where it's from, or its own links, and no way to bring in a list of local acts that editors keep. A record per artist and per band, with members, is the base for later work: public artist pages and linking events to acts. This change builds that base, admin-only.

## What Changes

- **Artist and Band records.** A person or solo act is an `Artist`; a group is a `Band`. An artist can be a member of any number of bands, each membership with an optional role ("guitar", "vocals") and years. Each record has a name, a home town and state, its own links (official site, Bandcamp), editors' notes, and what MusicBrainz says about it.
- **Import from a CSV or a Google Sheet tab.** One layout for both, which we design (below), keyed by an `Act_ID` column like the venue sheet's `Venue_ID`. A row creates or updates its record and its listed members; the import never deletes a record, and never overwrites what MusicBrainz or an editor set.
- **Enrichment from MusicBrainz.** For each record, find its MusicBrainz artist and store its ID and its open data: type, country and area, begin and end dates, the band's members and their roles and years (creating member artists as needed), genres, and links (official site, Bandcamp, Wikidata, Discogs). MusicBrainz's core data is public domain (CC0), so it may be stored.
- **A short introduction, from MusicBrainz and Wikipedia.** MusicBrainz's disambiguation note ("Boston indie rock band"), which is CC0. And, for an act MusicBrainz links to Wikidata, the opening paragraph of its English Wikipedia article, found through Wikidata and fetched from Wikipedia's summary API. It's kept word for word with its article link and revision, and credited wherever it's shown ("From Wikipedia", linked, under CC BY-SA 4.0), as Wikipedia's licence requires. Most small local acts won't have an article; those keep only the disambiguation note. Images in Wikipedia's summary aren't kept, since each has its own licence.
- **Last.fm only as evidence.** When a name matches several MusicBrainz artists, Last.fm can say which one it means (its page's MusicBrainz ID, and whether its bio places the act in a covered state), with the rules `resolve_artists_with_lastfm` already uses. Nothing from Last.fm is stored or shown, as its terms require.
- **Bandcamp only as a link.** Bandcamp has no public API (its API is only for labels and merch partners managing their own accounts), and its acceptable use policy forbids scraping and data mining. So nothing is read from Bandcamp: a record keeps a Bandcamp URL, typed by an editor, given in the import, or taken from MusicBrainz's links.
- **The admin.** Artist and Band admins with members inline, filters by state and by MusicBrainz match status, and actions to re-match or to set a record's MusicBrainz ID by hand.

### Not in this change

- Public artist or band pages, and anything shown to visitors.
- Linking events to these records; events keep naming artists by text, and the Spotify, Apple Music and YouTube links stay keyed by name.
- A scheduled import or enrichment. Both are run by hand for now.
- **Later: Bandcamp's embedded player.** Bandcamp offers an embed code on every album and track page ("Share / Embed"), which shows Bandcamp's own player, served by Bandcamp, the way it intends its music to be shown elsewhere. A later change, with the public pages, can let an editor (or the act) paste that code for a record, keep only the album or track ID it names, and show the player on the act's page. Nothing would be read from Bandcamp to get it. Using a scraping service instead (such as ScrapingBee's "Bandcamp API") was ruled out on 2026-10-29: it's still scraping, which Bandcamp's acceptable use policy forbids, and it hides who's asking, which the site's crawling rules don't allow.

## Capabilities

### New Capabilities
- `artist-records`: Artist and Band records and memberships, the CSV and Google Sheet import, MusicBrainz enrichment with Last.fm as evidence, Bandcamp links, and their admin.

### Modified Capabilities
None.

## Impact

- **Code:**
  - models `Artist`, `Band` and `BandMembership`, with a migration;
  - `core/artist_import.py` and an `import_artists` command (`--csv <path>` or `--sheet <id> --tab <name>`, reusing `core/google_sheets.py` and the `gog` reader);
  - `core/wikipedia.py`, a small client for Wikidata's English Wikipedia link and Wikipedia's page summary;
  - a MusicBrainz client for artist search and lookup (extending `core/music_ids.py`'s paced client), and an `enrich_artists_from_musicbrainz` command;
  - the admin.
- **Services:** MusicBrainz (free, one request a second, the contact user agent), Last.fm (free, existing key), and Wikidata and Wikipedia (free and keyless; Wikimedia asks for a user agent with contact details, which `core/user_agent.py` gives). Nothing new to pay for.
- **Licensing:** MusicBrainz core data (IDs, names, dates, areas, relationships, URLs) is CC0. Its genres and tags are "supplementary data" under CC BY-NC-SA, which allows this non-commercial site with credit; the design keeps them, credited, admin-only. Wikipedia's text is CC BY-SA 4.0: kept unmodified, with a link to the article and the licence wherever it's shown.
- **Data:** a new sheet the user makes, in the layout in design.md. Nothing existing changes.
