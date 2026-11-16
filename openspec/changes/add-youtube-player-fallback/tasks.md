## 1. Before building

- [ ] 1.1 Archive `improve-band-discovery` (its deck-autoplay exception to the player requirement is carried in this change's delta); verify `openspec validate add-youtube-player-fallback` passes and the player requirement's main text matches.

## 2. Playability and the weekly check

- [ ] 2.1 Extend `videos()` in `core/youtube.py` to read `status`, `contentDetails` and `contentRating` and return `playable` (design decision 6); verify with recorded JSON (key stripped) for public, private, unprocessed, US-blocked, US-not-allowed, age-restricted and not-embeddable videos.
- [ ] 2.2 Use `playable` in `match_youtube_artists` wherever it used `embeddable`, and re-read video links after 7 days (channel-only after 30); verify "Refresh keeps a live video", "Video removed", "Not playable in the US" and "Link no longer needed".
- [ ] 2.3 Add the song search for channel-only links, after unmatched names and within `--limit`, at most once every 30 days a link (design decision 5); verify "A song video on the channel" and "A video on another channel", with the Data API, Last.fm, Wikidata and MusicBrainz mocked.

## 3. The player

- [ ] 3.1 Build the YouTube player with the IFrame Player API on the `youtube-nocookie.com` host, loading `iframe_api` on the first click, with the channel-only playlist `UULF…`, falling back to the plain iframe when the script fails; verify "No player before a click", "Click opens the video", "Channel-only match plays its uploads", "One player across services", "Switched off" and "The API script doesn't load" with Playwright, the script routed to a stub.
- [ ] 3.2 Replace a player that reports an error with the fallback line in listings, and the next player in the deck (design decision 2); verify "A dead video in a listing", "A dead video in the deck" and "Nothing else to play" with the stub firing `onError`.

## 4. The report

- [ ] 4.1 Add `/youtube/unplayable` (no session or CSRF, YouTube ID formats only, 204 always, once an hour per ID) setting matched links' `checked_at` back, and send it from the page with `sendBeacon` on an error; verify "A report makes a link due" and "A malformed or repeated report", and that the page sends the beacon.

## 5. Finish

- [ ] 5.1 Check the privacy page still describes what loads from YouTube (the API script after a click, the player on `youtube-nocookie.com`); update `PRODUCTION.md` (the weekly playability check, the report, `UULF`) and verify they describe the shipped behavior.
- [ ] 5.2 Run the whole suite with the network blocked (styles compiled), and check the listing and the deck at 390px and 1440px with a stubbed failing player.
