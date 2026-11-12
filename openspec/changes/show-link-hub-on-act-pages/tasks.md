Issue: [#52 Show an act's Linktree (link hub) prominently on its artist or band page](https://github.com/natea/newenglandmusic/issues/52)

Issue: [#52 Show an act's Linktree link hub prominently on its artist or band page](https://github.com/natea/newenglandmusic/issues/52)

## 1. The hub link

- [x] 1.1 Add `link_hub_of(act)` to `core/views/act_page.py`, returning the "All links on <hub name>" label and address (falling back to a supported hub address in `website` when `link_hub_url` is empty; "All links" for an unsupported address; nothing when there is none), and pass it to the template; make `links_of` skip a website that `hub_for` recognises; verify with tests for Linktree, Solo.to, a hub only in `website`, an unsupported address and no address.
- [x] 1.2 Draw the link in `core/templates/core/band.html` in the placement of the chosen design, above the members and links, with its style in `band.scss` once the design is chosen; verify the order and that the Links row doesn't repeat it.
- [x] 1.3 Write the automated tests for the scenarios of "The link hub is shown prominently" and "The hub link stands apart from the other links": an act on Linktree, another hub, no link hub, not repeated among the links, a hub only in the website field, an unsupported address; run them with the network blocked.

## 2. Counting a hub as links

- [ ] 2.1 Change `invitation()` so a hub address counts as links, and, only when the hub is the act's sole links, both the visible line in `band.html` and the mail body in `invitation()` drop "links"; leave the wording unchanged otherwise; verify with tests.
- [ ] 2.2 Write the automated tests for the scenarios of the changed "Inviting the band to add more": the invitation (visible wording "photo, bio and links" kept), only a link hub, a hub and a missing photo, a hub with other links and a missing photo.

## 3. Finish

- [ ] 3.1 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/band-pages/spec.md` covered.
- [ ] 3.2 Check the page on a phone-width screen and verify the link is reachable without scrolling past the members.
