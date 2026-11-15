Issue: [#52 Show an act's Linktree (link hub) prominently on its artist or band page](https://github.com/natea/newenglandmusic/issues/52)

Issue: [#52 Show an act's Linktree link hub prominently on its artist or band page](https://github.com/natea/newenglandmusic/issues/52)

# Proposal

## Why

Linktree's robots.txt shuts out every crawler it doesn't name, ours included, and Linktree has no public API for reading another account's links. So the weekly link-hub job (`add-artist-link-hub-links`) can't fill an act's links from its Linktree. For now editors copy those links by hand (the owner's decision, 11 November 2026), and visitors should be able to reach the hub directly. Today the act's page never shows the hub: `links_of` in `core/views/act_page.py` lists only Website, Bandcamp, Instagram and YouTube.

## What Changes

- An artist or band page whose record has a link-hub address shows one clearly labelled link near the top, near the top of the card (placement follows the chosen screen design: under the next-show strip, or beside the meta line), named after the hub: "All links on Linktree", "All links on Solo.to", and so on. The hub's name comes from the supported hubs list in `core/link_hubs.py`.
- The link is separate from the "Links" row, which keeps listing Website, Bandcamp, Instagram and YouTube only. A hub address that sits in the website field is shown as the hub link and left out of the Links row, and acts with such an address still get the link before the weekly job copies it.
- An act with only a hub address counts as having links: its page no longer invites the act to send links (the invitation still asks for a photo or bio if one is missing; its line and mail wording drop "links" only when the hub is the act's only links, and are otherwise unchanged).
- Pages for acts with no hub address look the same as today.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities
- `band-pages`: adds "The link hub is shown prominently" and "The hub link stands apart from the other links", and modifies "Inviting the band to add more" so a hub counts as links. The existing "Links" requirement is not changed.

## Impact

- `core/views/act_page.py` (a `link_hub_of` helper next to `links_of`, `links_of` skipping a hub address in `website`, and the invitation check), `core/templates/core/band.html` (the hub link and the invitation line), `core/static`/`scss/band.scss` for the link's style.
- No model, migration, command or outside-service change; it reads `link_hub_url`, already stored. Tests in `core/tests/test_band_pages.py`, none touching the network.
- Needs a screen design: where the link sits on the card and how prominent it is.
- Builds on `add-artist-link-hub-links` (#44), which adds the hub fields and `hub_for`; if that change is not yet archived, this one depends on its code, not its spec text (the `artist-link-hubs` spec exists only in that change until it is archived).
