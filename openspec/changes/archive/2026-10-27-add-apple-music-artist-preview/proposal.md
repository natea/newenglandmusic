## Why

The Spotify play buttons (`add-spotify-artist-preview`) serve visitors who use Spotify. Many visitors use Apple Music instead. They should be able to sample a band the same way: with one click in the listing, in Apple's own player.

## What we found (tested 2026-10-27)

- **Apple's documentation doesn't mention artist embeds, but they exist.**
  - `https://embed.music.apple.com/us/artist/<id>` renders Apple's player with the artist's photo, name and a Play button.
  - For a visitor not signed in to Apple Music, **Play does nothing**: no audio loads. It presumably starts the artist's station, which needs a subscription.
- **Song and album embeds work for everyone.**
  - A song embed (`embed.music.apple.com/us/album/<album id>?i=<song id>`) is a compact player for one song.
  - An album embed (`/us/album/<album id>`) shows the track list.
  - Both played a 30-second preview at once without sign-in, and play full tracks for signed-in subscribers.
- **The Apple Music API lists an artist's most popular songs.**
  - Its `top-songs` view is documented as "Songs associated with the artist based on popularity in the current storefront".
  - It also searches the catalog for artists.
  - It needs an Apple Developer Program membership, which we have, and a developer token signed with a MusicKit key.
- **The free iTunes Search API needs no membership,** but doesn't document any popularity order. Its song list for Taylor Swift began with songs she's only featured on. It's no longer needed.

## What Changes

- **An Apple Music button per artist:** next to each artist's Spotify button, in the same row below the event's text. It appears only for artists matched on Apple Music.
- **What the button opens:**
  - Clicking it opens Apple's embedded player for the artist's **top song**, the first in Apple's `top-songs` view, below the row. It plays a preview for everyone, and the full song for subscribers.
  - Under the player, a "More by <artist> on Apple Music" link goes to the artist's page: the artist-level view, which Apple's artist embed can't play for most visitors.
  - Without JavaScript, the button is a link to the artist's Apple Music page.
- **Matching:**
  - A new daily command, `match_apple_music_artists`, searches the Apple Music catalog for the same artist names the Spotify matching uses (`event-artist-names`).
  - It links a name only when exactly one Apple Music artist has that exact name, ignoring case, accents and similar differences.
  - It stores the artist ID, their top song's ID, and that song's album ID.
- **Admin corrections:** as with Spotify, an editor can paste an Apple Music artist link, or mark a name as having no Apple Music artist.
- **Storage and refresh:**
  - Automatic matches, and every match's top song, are refreshed every 30 days.
  - Links are deleted 30 days after the last event that named the artist, as with Spotify.
- **One player at a time:** opening an Apple player closes a Spotify one, and the other way around.
- **Credentials:**
  - **The key:** `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY`, the MusicKit key's `.p8` contents.
  - **The token:** the site signs short-lived developer tokens from them on the server, so the private key never reaches a browser.
  - **The switch:** `APPLE_MUSIC_PREVIEWS` shows or hides the buttons, so matches can be reviewed before visitors see them.

## Capabilities

### New Capabilities
- `apple-music-artist-preview`: matching artist names to Apple Music artists and their top songs, admin corrections, storage and refresh, and the click-to-play Apple Music player in the events listing.

### Modified Capabilities
None. It reuses `event-artist-names` unchanged. The listing's row of play buttons comes from `add-spotify-artist-preview`, which isn't archived yet, so this change adds to that row without restating it.

## Impact

- **Depends on:** `add-spotify-artist-preview`, for the artist names, the button row and the player script.
- **New code:**
  - a model, `AppleMusicArtistLink`, with a migration and an admin page;
  - `core/apple_music.py`, an Apple Music API client that signs its own developer tokens;
  - the `match_apple_music_artists` command;
  - an Apple button and an Apple branch in the player script, which is renamed `artist_preview.js`.
- **Dependencies:** `PyJWT` and `cryptography`, to sign the ES256 developer token.
- **Cost:**
  - The Developer Program membership, already paid. API calls are free.
  - The first run makes about two calls per name for roughly 2,500 names. At half a second apart, that's about 40 minutes.
  - Weekly runs after that only cover new names and refreshes.
- **Terms:**
  - The player is Apple's own widget, with Apple's branding and links.
  - Whether a concert listing is an allowed use of Apple's promotional content is an open question in `design.md`, to settle before going public.
- **Setup (owner):** in the developer account, create a Media ID and a key with Media Services (MusicKit) enabled, then set the three credentials locally and on Render. See `design.md`.
