## Why

A YouTube button sometimes opens a black "Video unavailable" player, as Tune-Yards' did on 2026-11-16, even when the act has working Spotify and Apple Music buttons beside it. The site can't tell that YouTube's player failed, so the dead player stays. 471 of the 1,177 artists matched on YouTube (about 40%) are matched to a channel only, and their player plays the channel's whole uploads list, Shorts and live streams included, so whatever the channel posted last is what visitors get. And the monthly check of a matched video reads only whether it may be embedded, not whether it's private, blocked in the US or age-restricted, all of which also show "Video unavailable".

## What Changes

- **A player that won't play is replaced.** The YouTube player is loaded through YouTube's own IFrame Player API (only after a click, as now), which reports when a video can't be played. On that report, the dead player is removed and the visitor is offered the act's other players (Apple Music, Spotify, Bandcamp) or "Watch on YouTube ↗"; in the discovery deck, the card switches to its next player by itself.
- **The page tells the site.** The failure is reported to a small endpoint, which marks that YouTube link due for its next check, so a link that's dead is found and fixed within a day rather than a month. A report changes nothing a visitor sees by itself.
- **Channel-only matches skip Shorts.** A channel-only player plays the channel's full-length uploads (`UULF…`), not everything (`UU…`), so a Short or a live stream is never what plays first.
- **Channel-only matches get a song video where one can be found.** For an artist matched to a channel by ID, `match_youtube_artists` searches for the artist's top song (Last.fm's, as for song matches) and keeps a video only when it's on that same channel. Searches come out of the same daily budget (90), so the 471 clear over about a week.
- **The check reads whether a video can actually be played.** A matched video counts as playable only when it may be embedded, is public and fully processed, isn't blocked in the US, and isn't age-restricted. Video checks run weekly instead of monthly: 50 videos a quota unit, so about 25 units a week for every link.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `youtube-artist-preview`: the player detects a video it can't play and falls back; channel-only players play full-length uploads; channel-only matches look for a song video on the same channel; links are checked weekly for playability, not only embeddability; visitors' failure reports mark a link due.

## Impact

- **Code:** `core/static/core/js/artist_preview.js` (the YouTube player through the IFrame Player API, the fallback, the report), `core/templates/core/discover*` and `core/static/core/js/discover.js` (the deck's switch to the next player), a small report view and URL (`core/views/`), `core/youtube.py` (`videos()` reads `status`, `contentDetails` and `contentRating`), `core/management/commands/match_youtube_artists.py` (the playability rule, the weekly re-check, the song search for channel-only links).
- **Outside services:** YouTube's IFrame Player API script (`https://www.youtube.com/iframe_api`), loaded only after a visitor presses a YouTube button; the player itself stays on `youtube-nocookie.com`. The YouTube Data API's daily quota covers the song searches (within the existing 90) and the weekly video checks (about 25 units).
- **Order:** `improve-band-discovery` (built, not yet archived) also changes the player requirement, to let the discovery deck start a player after a visitor's action. This change keeps that exception; archive `improve-band-discovery` first.
- **No migration.** The report only moves an existing link's check date.
