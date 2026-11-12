Issue: [#52 Show an act's Linktree link hub prominently on its artist or band page](https://github.com/natea/newenglandmusic/issues/52)

## Context

`core/views/act_page.py` builds the page for both `Artist` and `Band`: `links_of(act)` returns (label, url) pairs for website, Bandcamp, Instagram and YouTube, `band.html` draws them in the "Links" row of the `act-fields` list, and `invitation()` shows the "Is this you?" line unless the act has a photo, a bio (or disambiguation note) and `links_of(act)`; the visible line in `band.html` ("Send us a photo, bio or links") and the mail body in `invitation()` both list photo, bio and links today. #44's pre-pass can leave a hub address in `website` (copying it to `link_hub_url` without clearing `website`). #44 added `link_hub_url` and `link_hub_status` to the shared act model and `hub_for(url)` in `core/link_hubs.py`, which returns the `Hub` (with its `name`) for a supported address. Linktree can't be read by the job, so editors copy its links by hand; this change only gives visitors the hub itself.

## Goals / Non-Goals

**Goals:** a labelled hub link near the top of the page; hub-only acts count as having links; other pages unchanged.

**Non-Goals:** reading Linktree or any hub (robots.txt forbids it), changing the link-hub job or editor screens, showing hub status or findings publicly, adding the hub to the CSV export, sitemap or structured data.

## Decisions

- **A separate helper, not an entry in `links_of`.** `link_hub_of(act)` returns `(label, url)` or `None`, with the label "All links on <name>" from `hub_for(url).name`. The address is `link_hub_url`, or, when that is empty, the `website` if `hub_for(website)` recognises it (so an act whose hub address sits only in `website`, before the weekly job copies it, still gets the link).
- **A hub in `website` is not repeated.** `links_of` skips a website for which `hub_for` is not `None`, so the hub appears once, as the labelled link, and not also as "Website". Every other `links_of` entry is unchanged, and an act whose website is an ordinary site is unaffected.
- **Invitation: the narrowest change.** A hub counts as links, so the test becomes "photo, bio, and (`links_of` or hub)". Only when the hub is the act's sole links does the wording drop "links", in both the visible line (`band.html`) and the mail body (`invitation()`); an act with a photo, bio and hub-only links gets no line, and one missing a photo gets "photo". In every other case (including acts with no hub) the line and body stay exactly as today.
- **Placement.** Follows the chosen sketch: A, B or an equivalent sits under the next-show strip and above the `act-fields` list; C sits in the meta line above the strip. Either way it is its own element, visible without scrolling on a phone. The `act-fields` condition is unchanged: a hub alone doesn't open an empty Members/Links list.
- **Unrecognised address.** `hub_for` returns `None` for an address an editor typed that isn't a supported hub; the label falls back to "All links". Editors can enter any URL in the admin, so the page must not fail.
- **Safe link.** Opened with `target="_blank"` and `rel="noopener"`, like the other links; it's a plain link with no tracking.
- **No new data or requests.** It reads `link_hub_url` already on the record; nothing is fetched at page view.

## Risks / Trade-offs

- A hub whose page has since vanished (`link_hub_status` "gone") would still be linked if we ignore status. See open questions.
- The Linktree name is a third party's trademark; we use it only as a plain-text label of where the link goes.

## Testing

All tests are Django `TestCase`s in `core/tests/test_band_pages.py`, using the test client and records made in the test database. No outside service is involved at page view, so nothing needs mocking: the page makes no request to Linktree or any hub, and the tests run with the network blocked as the rest of the suite does, so any request would fail them. Google Sheets, Anthropic, Ticketmaster, Eventbrite, SeatGeek, Spotify, Apple Music, YouTube, Last.fm, Wikidata, MusicBrainz, OpenStreetMap and Google Places are not touched.

## Open Questions

- Should the link be hidden when `link_hub_status` is "gone" (the hub page returned 404/410)? Proposed default: show it whatever the status, since the check can be wrong and editors can clear the address; the owner should confirm.
- The exact label wording for an unsupported address ("All links") and whether the hub's own capitalisation ("Solo.to", "Lnk.Bio") is kept; proposed: the names in the supported hubs list.
- Where on the card it sits and how prominent: to be settled in the screen design; the spec's placement follows the chosen sketch.
- The admin form already rejects unsupported hub addresses, so the "All links" fallback is defensive and should not be tested beyond the one scenario.

## Sketches

- [Option A: Joined line](sketches/a.html). One more line in the lavender next-show band, in the card's plain link style, so the hub reads as part of the show-and-links strip at the top. Risk: Quiet: it looks like any other link and may be missed, and the band becomes a three-part stack on a phone.

- [Option B: Bordered block](sketches/b.html). A white, plum-bordered block under the strip with a headline-sized link and a note that it leaves the site, making the hub the clearest thing on the card after the next show. Risk: Loud: it can outweigh the next show and the act's facts, and a heavy box for what may be only a few links.

- [Option C: Corner tab](sketches/c.html). A small outlined chip at the right of the meta line, above the show strip, kept apart from the Links row without taking a row of its own. Risk: Sits above the next-show strip, not under it as the proposal says, and can wrap or crowd a long meta line on narrow screens.
