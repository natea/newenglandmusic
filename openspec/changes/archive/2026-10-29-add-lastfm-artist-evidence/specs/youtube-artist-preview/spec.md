## MODIFIED Requirements

### Requirement: Otherwise, the artist's own recording of their top song is a match
When no channel is linked by ID, and the name is matched on Spotify or Apple Music on its own link (not a duo's or an occasion's), the command SHALL take the first of the top tracks on the name's Last.fm page, with no autocorrection, and that track's album from Last.fm. It SHALL do this only when the Last.fm bio doesn't say several acts share the name. It SHALL NOT use any song, album or other data from Apple Music or Spotify for this. Apple's MusicKit terms allow its API to be used only to give access to Apple Music, and Spotify's policy allows its metadata to be used only with its content.

It SHALL then search YouTube for videos with "<artist name> <song name>", with a maximum of 10 results. It SHALL then read each result's channel title, title, description and embeddable status.

A result SHALL confirm the artist when all of these hold:
- **the channel is the artist's:** its normalized title equals the artist's normalized name, or the artist's normalized name followed by " - Topic";
- **it names the song:**
  - for a Topic channel, the description has the line "<song> · <artist>" and the album's name, both normalized. When Last.fm gives no album, a Topic channel's video SHALL NOT confirm;
  - otherwise, the video title contains the song's normalized name;
- **it can be embedded.**

The first confirming result SHALL be recorded as matched, with its video ID and channel ID. A Topic channel's video SHALL be preferred over the artist channel's. The evidence SHALL be recorded as "topic-song" or "channel-song". When no result confirms, or the name has no Last.fm page or top tracks, the name SHALL be recorded as not found.

Names SHALL compare as normalized for Spotify. The song and album names SHALL be used only during the run, and SHALL NOT be stored.

#### Scenario: Topic channel recording
- **WHEN** the Last.fm top track for "The Ballroom Thieves" is "Archers" on "A Wolf in the Doorway", and a search for "The Ballroom Thieves Archers" returns a video from "The Ballroom Thieves - Topic" whose description reads "Provided to YouTube by …", "Archers · The Ballroom Thieves" and "A Wolf in the Doorway"
- **THEN** the name is matched to that video and channel, with evidence "topic-song"

#### Scenario: Same name, different band
- **WHEN** the only result from a channel titled "Epicenter" is titled "Epicenter - Live at the Fest", and the Last.fm top track is "Glass Hours"
- **THEN** the name is recorded as not found

#### Scenario: Cover or fan upload
- **WHEN** a result titled "The Ballroom Thieves - Archers (cover)" comes from a channel titled "guitarjoe"
- **THEN** it doesn't confirm the artist

#### Scenario: Not embeddable
- **WHEN** the only confirming video can't be embedded
- **THEN** the name is recorded as not found

#### Scenario: Spotify-only artist confirmed with its Last.fm top track
- **WHEN** "157frq" is matched on Spotify only, its Last.fm top track is "Spine" on "A World I Was Never a Part Of", and a search for "157frq Spine" returns "157frq - Spine (Official Music Video)" from the channel "157frq"
- **THEN** the name is matched to that video, with evidence "channel-song"

#### Scenario: Apple Music data isn't used
- **WHEN** "The Ballroom Thieves" is matched on Apple Music with a top song, and the command runs
- **THEN** it makes no request to Apple Music, and searches YouTube with the Last.fm top track

#### Scenario: Topic video with no album from Last.fm
- **WHEN** Last.fm gives "Archers" with no album, and the only result is a Topic channel video of "Archers"
- **THEN** it doesn't confirm the artist

#### Scenario: Shared Last.fm page
- **WHEN** a name's Last.fm bio begins "There are at least two bands using the name"
- **THEN** the command makes no YouTube search for it, and records it as not found

#### Scenario: Spotify-only artist with no ID link
- **WHEN** a name is matched on Spotify only, neither Wikidata nor MusicBrainz links a channel, and it has no Last.fm page or no top tracks
- **THEN** the command makes no YouTube search for it, and records it as not found

## ADDED Requirements

### Requirement: Matches found with Apple Music songs are confirmed again
Song matches made before Last.fm gave the songs used Apple Music top songs. Each link SHALL record which service gave the song behind a song match. Each automatic link with the evidence "topic-song" or "channel-song" whose song came from Apple Music SHALL be due on the next run, whatever its check date, and matched again from scratch with the Last.fm top track. When the new search confirms no video, the link SHALL be recorded as not found and its events re-rendered without the button. Links an editor set, and matches by Wikidata or MusicBrainz, SHALL be unaffected.

#### Scenario: Old match confirmed again
- **WHEN** "13 Scotland Rd" was matched to a Topic video using its Apple top song, and the same video confirms against its Last.fm top track
- **THEN** the link stays matched to that video, and is marked as checked now

#### Scenario: Old match not confirmed
- **WHEN** an old song match's name has no Last.fm top track that a video confirms
- **THEN** the link is not found, and its events lose the YouTube button

#### Scenario: Other links unaffected
- **WHEN** the next run starts after the change is deployed
- **THEN** links set by an editor, or matched by Wikidata or MusicBrainz, aren't searched again
