## Context

- The YouTube player is built in `core/static/core/js/artist_preview.js` (`youtubePlayer`): a plain iframe on `youtube-nocookie.com`, `embed/<video id>` for a video match or `embed/videoseries?list=UU<channel>` for a channel-only match, with a "More by … on YouTube" link. The discovery deck uses the same function, with `autoplay=1` after a visitor's action (`improve-band-discovery`).
- A plain iframe gives the page no signal when YouTube shows "Video unavailable".
- `match_youtube_artists` matches by a channel linked in Wikidata or MusicBrainz (no video) or by a song search; it re-reads matched links after 30 days with `videos()` (`part=snippet,status`, keeping only `embeddable`) or `channels()`. 706 links have a video and 471 a channel only (2026-11-16).
- On 2026-11-16, Tune-Yards' channel-only player showed "Video unavailable" in the listing; loading its `UU` and `UULF` playlists headless gave "unavailable" once and played once, so the cause isn't reproducible from here. The browser-side fallback covers whatever the cause.

## Goals / Non-Goals

**Goals:** no dead YouTube player left on screen; fewer channel-only players; dead links found within a day of a visitor meeting one.

**Non-Goals:** choosing which video best represents an act (the matching rules stay evidence-only); thumbnails or titles from YouTube (still not stored); autoplay outside the deck.

## Decisions

### 1. The IFrame Player API, loaded on the first click
On the first YouTube click, the page loads `https://www.youtube.com/iframe_api` once and builds the player with `new YT.Player(element, {host: "https://www.youtube-nocookie.com", videoId | playerVars: {listType: "playlist", list}, events: {onError}})`, keeping today's size, attributes and referrer policy. Nothing loads before a click, as now. `onError` fires for codes 2 (bad id), 5 (can't play in HTML5), 100 (removed or private) and 101/150 (embedding not allowed).
*Alternative:* a timeout that assumes failure when nothing plays. Rejected: it can't tell a slow start or a paused player from a dead one.

### 2. The fallback
In a listing, the dead player is replaced in place by one line: "YouTube won't play this here." followed by buttons for the act's other players already in the row (Apple Music, Spotify, Bandcamp), each opening as it does now, and "Watch on YouTube ↗" to the video or channel. In the discovery deck, the card loads its next player in the deck's order (Apple Music, Spotify, Bandcamp), asked to start as the deck's players are; with none, it shows the same "Watch on YouTube ↗" line. If the API script itself can't load, the player stays a plain iframe, as today.

### 3. The report
The page posts `{kind: "video" | "channel", id}` with `navigator.sendBeacon` to `/youtube/unplayable`, which needs no session or CSRF token (it carries nothing private and can only make a check happen sooner). The view finds matched links with that video or channel ID and sets their `checked_at` back to the epoch, so the next `match_youtube_artists` run re-reads them first. It answers 204 whatever it finds, accepts IDs only in YouTube's formats, and does at most one update per ID per hour (a cache key), so floods cost nothing.
*Alternative:* store reports in a table for editors. Rejected for now: the next run's check settles it, and the admin already shows link status.

### 4. Full-length uploads for channel-only players
A channel-only player's playlist is `UULF<channel id without "UC">`, YouTube's list of a channel's full-length uploads, which leaves out Shorts and live streams. The "More by … on YouTube" link still goes to the channel.

### 5. A song video for channel-only matches
For a link matched by channel only, the command runs the song search it already runs for unmatched names (the Last.fm top track, with the same rules), and keeps the first result that's on the same channel and playable, setting the link's video and keeping its evidence ("wikidata" or "musicbrainz"). A result on another channel is ignored, so this never changes which channel an act is. Channel-only links are searched after unmatched names, within the same `--limit` (90 a run), each at most once every 30 days.

### 6. Playable, not just embeddable, checked weekly
`videos()` asks for `part=snippet,status,contentDetails,contentRating` (still one unit per 50 IDs) and returns `playable`: `status.embeddable`, `status.privacyStatus == "public"`, `status.uploadStatus == "processed"`, no `contentDetails.regionRestriction` that blocks "US" (`blocked` containing it, or `allowed` not containing it), and no `contentRating.ytRating == "ytAgeRestricted"`. Matching uses it wherever it used `embeddable`. Matched links with a video are re-read when checked more than 7 days ago (channel-only and deletion rules keep their 30 days): about 1,200 links, 25 units a week.

## Risks / Trade-offs

- [`onError` doesn't fire for every "unavailable" screen, e.g. a playlist whose first video fails but whose next plays] → the player then plays the next video, which is fine; the weekly check still catches dead video links.
- [The IFrame API script comes from `www.youtube.com`, not the no-cookie domain] → it loads only after a click, as the player already does; the player itself stays on `youtube-nocookie.com`. The privacy page's sentence about YouTube covers it; checked in the tasks.
- [Someone posts reports for every link] → the next run re-reads at most every matched link, at 1 unit per 50; the per-ID hourly limit bounds it.
- [`UULF` playlists are a YouTube convention, not a documented API] → if one stops working, the player's `onError` falls back as for any failure; the design names it so it's easy to revert to `UU`.

## Testing

- **Browser (Playwright):** the IFrame API script is routed to a stub `YT.Player` that renders a placeholder and calls `onError` on cue; tests cover the fallback line in a listing, the deck switching to its next player, a failed API script leaving a plain iframe, and the `sendBeacon` call. No request reaches YouTube.
- **Django:** the report view (204, the link's `checked_at` moved, bad IDs ignored, the hourly limit); `videos()` on recorded JSON with the key stripped (`core/tests/fixtures/`) for public, private, unprocessed, US-blocked, age-restricted and not-embeddable videos; the command's weekly re-check and the channel-only song search with the Data API, Last.fm, Wikidata and MusicBrainz mocked as the existing tests do.
