## Context

- **Links today:**
  - `SpotifyArtistLink` and `AppleMusicArtistLink` record each name as matched, ambiguous, not found or none, with a source of automatic or editor;
  - an editor's link is never searched for or changed;
  - automatic links are searched again after 30 days;
  - ambiguous links store no artist ID.
- **Already built that this reuses:**
  - `core/music_ids.py` reads MusicBrainz: one request a second, with 503 retries and a `MusicBrainzBusy` error;
  - `match_youtube_artists` and `core/youtube_links.py` run the song check (`confirming_video`) from a song name and an album name.
- **Last.fm, measured 2026-10-28 with our key:**
  - the root is `https://ws.audioscrobbler.com/2.0/`, with `method`, `api_key` and `format=json`;
  - `artist.getInfo` gives `mbid` (often empty for small acts), `stats.listeners`, `bio.summary` (truncated at 300 characters) and tags;
  - `artist.getTopTracks` lists tracks by play count;
  - `track.getInfo` gives a track's album;
  - shared names are one page, whose bio usually begins "There are at least two…" or "There are several…", then numbers the acts;
  - the documented limits are vague: being reasonable, and no several calls a second. Error 29 means rate limited, 26 a suspended key, 6 not found.
- **Sample of 20 ambiguous names:** 19 Last.fm pages, 16 with an MBID. 6 MusicBrainz artists linked Spotify, 7 had an area, and 8 couldn't be checked because of MusicBrainz 503s.

## Goals / Non-Goals

**Goals:**
- Turn ambiguous names into matches only on two independent pieces of evidence: an ID chain (Last.fm, then MusicBrainz, then Spotify or Apple Music) and the place or dominance rule.
- Give names matched only on Spotify a song to confirm on YouTube.

**Non-Goals:**
- Showing anything from Last.fm, such as tags, bios, similar artists or genres. That would need Last.fm's written approval first.
- Autocorrecting names with `artist.getCorrection`. A corrected name is a different name, which the matching should handle on its own terms.
- Resolving names that are "not found". Their problem is spelling, not sharing.
- Using the Last.fm secret or any user calls.

## Decisions

**1. The ID chain decides the artist, and place or dominance decides whether to trust it.**
- **Why the chain:** a Last.fm page merges every act with the name. Its MBID is the one act that page's editors linked, usually the best-known. MusicBrainz then links that act to exactly one Spotify or Apple Music artist, so the chain names an artist, not a guess.
- **Why a second test:** the chain alone would pick the famous act for a local band's gig. The second test asks whether that act is plausibly the one playing here:
  - **local:** its MusicBrainz area is in a covered state, found by following MusicBrainz's "part of" links up to an area with an ISO 3166-2 code such as US-MA. Each area is looked up once per run. The first real run (2026-10-28) matched areas by town name, and counted Windsor (Ontario), Brighton and Liverpool (England) and Washington as local, because the site has venues in Windsor, CT, Brighton, MA, Liverpool, NY and Washington, DC. Or or its bio names a covered state ("Western Massachusetts", "Worcester, MA") and isn't a shared page's. The covered places come from the database: the states of venues with a state, and their `city_town` values. A town alone in a bio doesn't count. In the first dry run (2026-10-28), "Alien"'s shared bio counted as local because it mentioned someone named Johnson, which matched Johnson, VT;
  - **dominant:** at least 100,000 listeners, and no shared-name note in the bio. Then the act is far better known than any namesake, and a listing venue is far likelier to book it. Spotify's own ambiguity comes from tiny same-name uploads.
- **Alternatives rejected:**
  - comparing Last.fm top tracks with each candidate's Spotify top tracks: the Spotify allowance is the bottleneck, and the merged page's tracks mix the acts;
  - place alone: it would never resolve touring acts, which are most of the ambiguous names.
- **Threshold:** 100,000 listeners. Bonobo (2.1M), 2hollis (937k), Brian Fallon (86k) and Cory Wong (214k) show the range. Brian Fallon falls below it, but he's from Red Bank, NJ, so he'd pass only if the site covers NJ. Keep the threshold as a constant, and revisit it after a week's run.

**2. A third source value, "evidence".** A new `Source.EVIDENCE` on both link models, with a migration that only changes the choices. Each model's `is_due` treats it as it treats an editor's link: Apple refreshes the top song, and Spotify never re-checks it. A new `evidence_checked_at` field (nullable) on both models records when the Last.fm step last considered the link. It holds only a timestamp, so it stores no Last.fm data. The admin shows the source, and an editor's save overrides it as usual.

**3. One command, after the Apple Music matching.** `resolve_artists_with_lastfm [--names] [--limit 300] [--dry-run]` takes the ambiguous Spotify and Apple Music links due for consideration:
- reads Last.fm once per name;
- reads MusicBrainz once per MBID, with `inc=url-rels`; the area and begin area come in the same response;
- for Apple Music matches, calls `AppleMusicClient.top_song`;
- re-renders through `rebake_events_naming`;
- records a `JobRun` (`RecordedCommand`), with counts considered, resolved local, resolved dominant, stayed ambiguous, re-checked, reverted and failed.

`--limit` caps the names considered, to bound the run time: up to 300 Last.fm requests at 0.5 s, plus up to 300 MusicBrainz requests at 1.1 s, about 8 minutes.

**4. The YouTube step's songs come from Last.fm only.**
- **Why:** Apple's MusicKit terms (DPLA §3.3.6 D) limit API calls to "facilitating access to Your end users' Apple Music subscriptions", and forbid using "music-related text … separately from music playback". Searching YouTube for an Apple top song is neither. Spotify's metadata rule is the same.
- **How it works:** for a name matched on Spotify or Apple Music on its own link, `match_youtube_artists`:
  - calls `artist.getInfo`, and skips the name when the bio flags a shared name;
  - calls `artist.getTopTracks(limit=1)`, then `track.getInfo` for the album;
  - lets `confirming_video` decide, as before;
  - counts the searches against the same `--limit`.
  
  The command no longer makes an Apple Music client.
- **A Topic video needs an album:** it confirms only when Last.fm gives an album, since the album line is what ties a Topic video to this act and not a namesake.
- **Alternative rejected:** keeping Apple's songs for Apple-matched names. It's what the terms forbid, and Last.fm's top tracks serve the same purpose.

**4a. Re-matching the old song matches.**
- **The marker:** `YouTubeArtistLink.song_source`, blank, "apple" or "lastfm", says which service gave the song behind a song match. A data migration sets "apple" on every automatic link with evidence "topic-song" or "channel-song".
- **The re-match:** the command treats those links as due whatever their check date. It re-matches each from scratch (ID links, then the Last.fm song) and records the new result with "lastfm".
- **Why not just delete them:** most will confirm again, so their buttons stay. Deleting would drop the buttons until the next morning.

**5. The place rule as a pure function.** `core/artist_evidence.py`:
- `covered_places()` returns the states with their full names, and the towns, from `Venue`;
- `names_covered_place(text, places)` matches a whole-word full state name, a town, or "Town, ST" in a MusicBrainz area or a bio;
- `shares_name(bio)` finds the shared-name notes;
- `is_dominant(listeners, bio)` applies the listener threshold and the note check.

All are unit-tested without the network.

**6. Key handling.** Last.fm takes the key only as a query parameter, so `core/lastfm.py`:
- builds requests through a session with no request logging;
- writes errors from Last.fm's `error` code and `message` only;
- never prints a URL.

Tests check that no error text contains the key.

**How it's tested.** Nothing reaches the network, and the suite passes with outbound requests blocked.
- **Last.fm:** `core.lastfm.LastFm` takes an injectable session and sleep. Tests use a fake session that answers `artist.getInfo`, `artist.getTopTracks` and `track.getInfo` from hand-written JSON in Last.fm's documented shapes, in `core/tests/fixtures/lastfm/`, with no key in them. That includes the Bonobo, DJ Lucas and Dead Weight examples, and errors 6, 26 and 29. It also asserts that requests carry the user agent and are paced.
- **MusicBrainz:** the existing `FakeWeb` in `core/tests/youtube_fixture.py` gains artist lookups by MBID, with area, begin area and Spotify and Apple Music URL relations, plus its 503 mode.
- **Apple Music:** `FakeAppleMusic` answers the top-song lookups, as in the existing tests.
- **Spotify:** no Spotify request is made by this change. The tests assert that `match_spotify_artists` makes no search for an evidence link, using the existing `spotify_fixture`.
- **YouTube:** `FakeWeb` answers searches and video lookups for the Last.fm route. The tests patch `AppleMusicClient` in `match_youtube_artists` to fail if it's ever made, to show that no Apple request is made.
- **The daily job:** `test_scheduled_jobs.py`'s `DAILY` list gains the step.

## Risks / Trade-offs

- **[A wrong MBID on Last.fm]** → Last.fm's editors sometimes link the wrong act. Requiring the MusicBrainz name to equal ours, and exactly one linked artist on the service, catches most cases. Editors can override, and the 30-day re-check catches fixes made upstream.
- **[A dominant act's namesake really is playing]** → For example, a local cover band called after a famous one. The shared-name note blocks the cases Last.fm knows about. The rest is the accepted trade-off. Each resolution is listed in the job output, and the admin can filter by the "evidence" source.
- **[MusicBrainz 503s]** → It was down for long stretches on 2026-10-28. Lookups stop for the run, and names are left for the next one, rather than being marked as considered.
- **[Last.fm's terms]** → It allows non-commercial use only, and wants written approval for public pages that use the API, and a credit. We display nothing, but its data shapes which buttons appear. Before going public, ask partners@last.fm. Add this to PRODUCTION.md's launch checklist beside the Google Places and YouTube items. If Last.fm says no, turning the step off and reverting evidence links is one command away.
- **[The key in URLs]** → Last.fm requires it there. It is never logged or printed, and requests go over HTTPS.

## Migration Plan

1. Deploy the migration and code.
2. Run `resolve_artists_with_lastfm --dry-run --limit 30` locally, and check each resolution by hand.
3. Run it for real locally, then set `LASTFM_API_KEY` on Render, with the user's approval.
4. The daily job takes over.

**Rollback:** `resolve_artists_with_lastfm --revert` sets every evidence link back to ambiguous and re-renders its events. Then remove the step from `bin/daily.sh`.
