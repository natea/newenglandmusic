## Why

Visitors who don't use Spotify or Apple Music have no way to hear an act from the listing, and YouTube is where most people can listen without an account. YouTube makes same-name mistakes worse: a search for a small local band's name mostly returns other bands, covers and fan uploads. So a YouTube button must be shown only when we are very sure the music is by the artist named on the event.

## What Changes

- **A YouTube button beside the Spotify and Apple Music buttons.** It shows only for artists already matched on Spotify or Apple Music, since those matches already established who the artist is. A YouTube match must then be tied to that same artist by evidence. A matching name alone is never enough. Clicking the button opens YouTube's own embedded player (`youtube-nocookie.com`), and nothing from YouTube loads before the click.
- **`match_youtube_artists`, a new daily step.** It finds YouTube matches in this order and keeps the first that passes:
  1. **Linked by ID in open music databases:**
     - Wikidata items that carry the artist's Spotify ID or Apple Music ID and a YouTube channel ID;
     - MusicBrainz artists whose links include both the artist's Spotify page and a YouTube channel.
     
     These sources are free and use no YouTube quota.
  2. **The artist's own recording of their Apple Music top song:**
     - search YouTube for "<artist> <top song>";
     - accept a video only if it comes from the artist's channel, or from YouTube's auto-generated "<artist> - Topic" channel;
     - and its title or its "Provided to YouTube" description names that same song and album.
     
     Two acts with the same name rarely have a song with the same title on an album with the same title.
  
  Anything else gets no button.
- **What a button plays:** the confirmed song's video, or, for a channel found by ID, that channel's uploads, in YouTube's own player.
- **Editors can override.** In the admin, an editor can paste a YouTube channel or video URL, or mark an artist as having no YouTube, as they can for Spotify and Apple Music.
- **Required by YouTube's terms:**
  - stored IDs are re-checked within 30 days, and removed once a video is gone or can no longer be embedded;
  - a new `/privacy` page says the site uses YouTube API Services and links to Google's Privacy Policy and YouTube's Terms of Service;
  - the player is YouTube's own, unmodified, nothing covers it, and it's at least 200 × 200 px.
- **Not used:** the custom-skin players suggested (pixelgridui/youTube-player, csPlayer). Both replace YouTube's controls with their own. YouTube's Required Minimum Functionality forbids changes to the player beyond its API documentation, and any elements over it.

## Capabilities

### New Capabilities
- `youtube-artist-preview`: covers:
  - matching artists to YouTube channels and videos on confirming evidence;
  - editor overrides;
  - the 30-day refresh;
  - the click-to-play YouTube button;
  - the privacy page's YouTube disclosures.

### Modified Capabilities
- `scheduled-jobs`: the daily job gains `match_youtube_artists`, after the Apple Music matching.

## Impact

- **Code:**
  - `core/youtube.py`, the YouTube Data API client;
  - `core/youtube_links.py`;
  - `core/music_ids.py`, the Wikidata and MusicBrainz lookups;
  - a `YouTubeArtistLink` model, its migration and its admin;
  - the `match_youtube_artists` command;
  - the button in `core/templates/core/event.html`, from `core/artist_previews.py`;
  - the player in `core/static/core/js/artist_preview.js`;
  - a `/privacy` page and a footer link to it;
  - one new line in `bin/daily.sh`.
- **Apple Music:** the top-song lookup also returns the song and album names for the YouTube check. They're used only during the run and never stored, so the Apple Music spec doesn't change.
- **New key:** `YOUTUBE_API_KEY`, a Google Cloud key restricted to the YouTube Data API v3. It's sent in the `X-goog-api-key` header, never in a URL. Add it to `.env`, `.env.example`, `render.yaml` and PRODUCTION.md. Also add the switch `YOUTUBE_PREVIEWS`.
- **Quota:** the free 10,000 units a day.
  - Each song search costs 101 units (a search plus a video lookup), so the command searches for at most 90 artists a day.
  - The 30-day refresh reads 50 videos or channels per unit, so it costs almost nothing.
  - Wikidata and MusicBrainz use no YouTube quota.
  - Spending money isn't possible without enabling billing, which this change doesn't do.
- **Coverage (measured 2026-10-28):**
  - Wikidata links 33 of the 254 Spotify-matched artists to a YouTube channel.
  - MusicBrainz links 4 of a sample of 20.
  - The song search can reach Apple-matched artists with a top song (115 locally).
  - Artists matched only on Spotify (171 locally) get a button only through Wikidata or MusicBrainz. Expect buttons for roughly a third to a half of matched artists at first, all of them confirmed.
- **Launch checklist:** using the YouTube API adds a privacy-policy requirement beside the open Google Places question. See the design's risks.
