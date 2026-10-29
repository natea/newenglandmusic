## Why

Two gaps leave play buttons missing for acts we could be sure of:
- **Shared names stay ambiguous.** 123 names locally are "ambiguous" on Spotify and 73 on Apple Music, because each catalog has several artists with that name. Most belong to a well-known touring act that shares its name with tiny ones, like Bonobo, Brian Fallon and Cory Wong. Others belong to local acts, like DJ Lucas from Western Massachusetts.
- **Spotify-only artists can't be confirmed on YouTube.** The YouTube song check needs the artist's Apple Music top song, so the 171 names matched only on Spotify (locally) get a YouTube button only through Wikidata or MusicBrainz.

Last.fm can fill both gaps behind the scenes:
- its artist pages carry a MusicBrainz ID, which MusicBrainz links to the act's Spotify and Apple Music pages;
- its bios often say where the act is from, and flag shared names ("There are at least two bands using the name…");
- it lists the act's most-played tracks.

In a sample of 20 ambiguous names (2026-10-28), 16 had a MusicBrainz ID on Last.fm. 6 of those were linked to a Spotify artist, and 8 more couldn't be checked because MusicBrainz was answering 503.

## What Changes

- **A new daily step, `resolve_artists_with_lastfm`,** run after the Apple Music matching. For each automatic Spotify or Apple Music link that is ambiguous, it:
  - reads the name's Last.fm page (`artist.getInfo`) for its MusicBrainz ID, bio and listener count;
  - looks that ID up on MusicBrainz, for the act's Spotify and Apple Music links and its area;
  - matches the name to the linked Spotify or Apple Music artist only when the MusicBrainz artist has the same name, and one of these holds:
    - **place:** the MusicBrainz area, or the Last.fm bio, names a state the site covers, or a town where it has a venue;
    - **a dominant act:** at least 100,000 Last.fm listeners, and a bio that doesn't say several acts share the name.
  
  Anything else stays ambiguous.
  
  A resolved link is recorded with the source "evidence". The Spotify and Apple Music matching then never search for it again or change its artist, as they treat an editor's link. Apple Music links resolved this way get their top song looked up as usual.
- **YouTube songs from Last.fm only, not Apple Music.**
  - **Why:** the YouTube song check searched for each artist's Apple Music top song. Apple's Developer Program License Agreement, §3.3.6 D, forbids calling the MusicKit APIs "for purposes unrelated to facilitating access to Your end users' Apple Music subscriptions". It also says "music-related text from the MusicKit API may not be used separately from music playback". Using Apple's song names to find recordings on YouTube is both. Spotify's policy is similar: "metadata … may only be used in connection with the underlying content".
  - **What changes:** `match_youtube_artists` takes the song, and its album, from the name's Last.fm page instead, for every name matched on Spotify or Apple Music on its own link, unless the Last.fm bio flags a shared name. It makes no Apple Music request.
  - **Existing matches:** the 35 local song matches found with Apple's songs (and those on Render) are matched again from scratch with the Last.fm track on the next run, and lose their button if it doesn't confirm them. A new `song_source` field, set to "apple" on them by a migration, marks them. It records which source gave the song, not the song.
- **Nothing from Last.fm is shown or stored.** Pages show no Last.fm text, tags, numbers or images, and links store only the Spotify, Apple Music and YouTube IDs they store now. The Last.fm data is read during the run and then discarded.
- **Requests are paced, and stop cleanly on errors.** Last.fm gets at most two requests a second, with the site's user agent. Error 29 (rate limit) or a suspended key stops the run, keeping what it found. A MusicBrainz outage stops the resolving until the next run.

## Capabilities

### New Capabilities
- `lastfm-artist-evidence`: covers:
  - the Last.fm client and its key;
  - the place and dominant-act rules;
  - resolving ambiguous Spotify and Apple Music links, and how the matching then treats them;
  - pacing;
  - what is never shown or stored.

### Modified Capabilities
- `youtube-artist-preview`:
  - the song check takes its song from Last.fm, not Apple Music;
  - matches found with Apple's songs are confirmed again.
- `scheduled-jobs`: the daily job gains `resolve_artists_with_lastfm`, between the Apple Music and YouTube matching.

## Impact

- **Code:**
  - `core/lastfm.py`, the client;
  - `core/artist_evidence.py`, the place and dominant-act rules;
  - the `resolve_artists_with_lastfm` command;
  - a MusicBrainz artist lookup in `core/music_ids.py`;
  - a new "evidence" source on `SpotifyArtistLink` and `AppleMusicArtistLink`, with a migration;
  - `match_youtube_artists` taking its songs from Last.fm only, with no Apple Music client;
  - a `song_source` field on `YouTubeArtistLink`, with a migration that marks the existing song matches;
  - one line in `bin/daily.sh`.
- **Keys:** `LASTFM_API_KEY`, already in `.env`. The secret isn't needed, because these are read-only calls. Add the key to `.env.example`, `render.yaml` and PRODUCTION.md. It goes in a URL parameter, as Last.fm's API offers no header for it, so it is kept out of logs and error messages.
- **Cost:** free. Each ambiguous name costs one Last.fm request and up to one MusicBrainz request. Each name the YouTube step searches for costs up to three Last.fm requests (its page, its top tracks, then the track's album), and draws on the existing 90 YouTube searches a day. Re-matching the old song matches uses part of one or two days' searches.
- **Last.fm's terms, which need a decision before launch:**
  - Use must be non-commercial.
  - Public pages that use the API need Last.fm's written approval, and Last.fm must be credited with a link.
  - Even though nothing from Last.fm is displayed, its data decides which buttons appear. Add this to PRODUCTION.md's launch checklist: ask Last.fm (partners@last.fm) whether evidence-only use needs approval or a credit.
