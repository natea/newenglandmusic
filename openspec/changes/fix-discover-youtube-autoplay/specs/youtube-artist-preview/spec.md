## ADDED Requirements

### Requirement: The deck's YouTube player may be controlled through YouTube's player API
The band discovery deck's YouTube player MAY be created with `enablejsapi=1` and `origin=<the site's origin>` added to its embed address, so the page can send it YouTube's documented player commands and read its state messages. The player SHALL stay YouTube's own, unchanged, with nothing drawn over it, at least 200 px wide and tall, and the page SHALL ask only one player at a time to play. The listings' players SHALL NOT carry `enablejsapi` or `origin`, and SHALL NOT be sent commands.

#### Scenario: The deck's player carries the API parameters
- **WHEN** a visitor on `/discover` has pressed Start and the first card is matched on YouTube
- **THEN** the iframe's src is the `youtube-nocookie.com` embed with `autoplay=1`, `playsinline=1`, `enablejsapi=1` and `origin` set to the page's origin

#### Scenario: The listing's player carries none of them
- **WHEN** a visitor clicks a YouTube button on the homepage
- **THEN** the iframe's src has no `autoplay`, `enablejsapi` or `origin` parameter, and the page sends it no message
