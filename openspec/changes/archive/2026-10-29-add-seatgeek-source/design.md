## Context

- **Split from `add-eventbrite-seatgeek-sources`** on 2026-10-26. The Eventbrite half, now `add-eventbrite-source`, adds the pattern this follows for a second API: an organizer link on the venue, an `eventbrite` event source, precedence in `fetch_events.select_targets`, and `eventbrite failed:` problem notes.
- **The Ticketmaster pattern:** `match_ticketmaster_venues` links venues using `core/venue_matching.py` (`names_match`, `distance_km`, `spelling_variants`) and its own `find_match`, preferring listings with events. `fetch_ticketmaster` records failures as `ticketmaster failed:` notes, which `is_problem` recognises by prefix.
- **Platform counts from the saved source checks:** etix 21, dice 10, tixr 9, axs 4; the rest are smaller.
- **What the API offers** (SeatGeek's developer docs, read 2026-10-29, and two test requests):
  - a free client ID, sent as a query parameter or by HTTP Basic Auth; the secret is optional
  - `/2/venues`, filtered by `city`, `state`, `postal_code` or `q`, returning `location`, `address` and `url`
  - `/2/events`, filtered by `venue.id` (several IDs separated by commas), `datetime_utc.gte` and `taxonomies.name`, paged by `per_page` and `page`
- **What it doesn't offer:** no ticket listings and no prices; `stats` comes back empty. No images either: public responses leave them out, and the API grants no licence to them. An event's `links` name resale sites (StubHub, RapidSeats) without URLs, and `integrated` names the primary seller (e.g. Ticketmaster) and its event ID, never a link to the Etix or AXS page.
- **`/events` is capped at 10,000 results** from 2026-01-01. SeatGeek recommends its Bulk Catalog API instead: hourly JSONL dumps of events, venues and performers, and a feed of changes from the last hour. Queries for a few venues stay far below the cap.

## Goals / Non-Goals

**Goals:**
- Venues whose ticketing pages fail, and that Ticketmaster and Eventbrite don't cover, get their events from SeatGeek, within its terms.
- SeatGeek behaves like the other API sources: linked by an admin-visible ID, imported unapproved, labelled by kind, with problems reported per venue.
- No duplicate events when a venue is reachable more than one way.

**Non-Goals:**
- Prices. SeatGeek's API returns none, so SeatGeek events have no price bucket.
- Sending people to SeatGeek. Its pages sell resale tickets; see the link decision below.
- SeatGeek's affiliate program (held off on 2026-10-29).
- SeatGeek's images, which the API neither returns nor licenses.
- Searching SeatGeek for venues we don't list.

## Decisions

**A coverage check gates the build.** `measure_api_coverage` gets a SeatGeek check: search the venue by name and state, match with the shared `find_match`, and count its upcoming concerts. The results go into Open Questions and are shown to the user. Groups 2 to 4 are built only if the user wants SeatGeek.

**SeatGeek matching reuses the Ticketmaster rules.** `find_match` is moved into `venue_matching` as a shared function that takes each source's candidate dicts. Both commands call it, so SeatGeek gets the same preference for listings with events, the exact-name rule and the 1 km limit. Concerts are kept by SeatGeek's taxonomy (`concert`, `music_festival`). Other events are counted as left out, as with Ticketmaster's non-music events.

**SeatGeek comes last in the precedence.** A venue's source becomes the first linked API: Ticketmaster, then Eventbrite, then SeatGeek, never over iCal or JSON-LD. SeatGeek is the broadest, but includes resale, so it only fills gaps. Its events get the `external_id` prefix `seatgeek:` and the `seatgeek` event source.

**SeatGeek links are stored, not shown (decided 2026-10-29).** An event's SeatGeek `url` goes in `Event.source_url`, which the site never displays; admins see it on the event. Its `hyperlink` and `ticket_hyperlink` are the show's own Etix or AXS page when one is found (see below), else the venue's own ticket page: a new `Venue.ticket_page_url` (its Etix, AXS or other listing), or else the venue's website. SeatGeek gives no per-event link to the primary seller, so the link is to the venue's listing, not the show. Ticketmaster and Eventbrite events keep linking to the show, since those are the primary sellers.

**Links to the show's own page (decided 2026-10-29).** SeatGeek's API never says where a show is sold: an Etix-sold Toad's Place show has no Etix ID or URL, only resale sellers' IDs without URLs. But most venues' own sites link each show's page on their seller. A sample of the 24 SeatGeek-only venues (`logs/ticket-links-sample-2026-10-29.log`) found each show's Etix or AXS page linked from 15 of their sites (10 to 46 shows each), and a venue page (`etix.com/ticket/v/<id>`, `axs.com/venues/<id>/…`) on 5. So `fetch_from_seatgeek` also reads each SeatGeek venue's events page (its saved `events_page`, else its saved `url`, else its website), once a run, and its homepage too: the first real run (2026-10-29) showed the saved events page is sometimes one show's page or a booking form, with one show link or none, while the homepage lists the shows (The Webster, Ottobar, Thunderbird, Sellersville). At most two pages a venue, and their links are combined:
- **Politely:** with the honest user agent, `robots_allows` from `check_event_sources`, and a timeout. Only the venue's own site is read, never Etix or AXS, which block crawlers. That's about 24 pages a day.
- **Show links:** `etix.com/ticket/p/<id>/<slug>` and `axs.com/events/<id>/<slug>`. A SeatGeek event matches a show link whose slug starts with the slugified title, or with its first performer's name; Etix slugs are the title, then the town and venue (`as-i-lay-dying-new-haven-toads-place-of-new-haven`). Only one distinct link may match: a recurring title ("Saturday Night Dance Party") matches several and falls back. URLs carry no date, so a title is the only key.
- **Venue links:** `etix.com/ticket/v/<id>` and `axs.com/venues/<id>/<slug>`. When the venue's ticket page is blank and the page links exactly one, it's saved there with `queryset.update()`. A ticket page that's already set, typed by an editor or filled in before, is never changed automatically; an editor clears it to have it filled in again.
- **Failures:** a page that can't be read, or that robots.txt disallows, is a note, not a problem. The events are still saved, with the fallback links.

The module `core/event_fetching/ticket_links.py` holds the link patterns and the matching, and has its own tests on recorded venue HTML (`core/tests/fixtures/ticket_links/`).

**Why a new field rather than the saved events page (decided 2026-10-29).** The coverage check showed the saved `events_page` is often not a ticket page (see Open Questions). `ticket_page_url` is not synced from the sheet, and blank by default. An admin can set it, and it's also filled in from the venue's own site (see above). It's saved with `queryset.update()` where possible, since it doesn't change how existing events render.

**SeatGeek replaces JSON-LD only when it has more (decided 2026-10-29).** A SeatGeek-linked venue whose source is JSON-LD is still crawled first. After the crawl, its SeatGeek concerts are fetched too, and if there are more of them than the JSON-LD's upcoming events, the run uses SeatGeek's events and drops the JSON-LD's, with a note giving both counts. Otherwise the JSON-LD's are kept and SeatGeek's are dropped. It's decided afresh each run, like the fallback when a feed fails, so no setting is stored. Unapproved JSON-LD events left from earlier runs are counted in the report, as for Eventbrite, not removed. iCal feeds are left alone: none of the SeatGeek venues has one.

**Failures and keys.** `seatgeek failed:` is added to `PROBLEM_PREFIXES`. The client follows `TicketmasterClient`. It sends the client ID by HTTP Basic Auth, so the ID is never in a URL, error message or log line. `SEATGEEK_CLIENT_SECRET` is in `.env` but not used: the public endpoints don't need it.

**Testing:** recorded JSON responses in `core/tests/fixtures/seatgeek/` with the client ID stripped, replayed through a fake session; `fetch_events` tests patch the client. The suite runs with outbound network blocked.

## Risks / Trade-offs

- [SeatGeek resells tickets for shows sold elsewhere.] → Its links aren't shown; listings link to the venue's own ticket page.
- [The venue's ticket page is a listing, not the show's page, so people have one more click.] → Only where the venue's site doesn't link the show itself.
- [A title match picks the wrong show.] → Only a single distinct matching link is used; recurring titles fall back to the list. Admins see the link on the event.
- [Reading venue sites every day.] → One page per SeatGeek venue, the honest user agent and robots.txt, as `check_event_sources` already does weekly for every venue.
- [A venue with no saved events page and no website gets no ticket link.] → The event is saved without one, for an admin to fill in.

## Migration Plan

1. One additive migration adds `Venue.seatgeek_venue_id`, `Venue.ticket_page_url` and the `seatgeek` event source.
2. Run the coverage check, then `match_seatgeek_venues --dry-run`, then for real.
3. Release through `main`.

**Rollback:** revert. The field can stay.

## Open Questions

- **Coverage (measured 2026-10-29, `logs/measure_api_coverage-seatgeek-2026-10-29.log`):** of the 82 active venues linking Eventbrite, Etix or AXS (the latest full fetch recorded no problem venues), SeatGeek matched 52. 32 have upcoming concerts there (349 concerts), and **21 of those aren't linked to Ticketmaster or Eventbrite**, so SeatGeek would be their only API. They include 16 of the 24 Etix and AXS venues, e.g. The Sinclair (47 concerts), Starland Ballroom (24), Thunderbird (22), Preserving Underground (18) and Toad's Place (12). Another 12 had no certain match, though several have a listing within 0.1 km under another name (Spruce Peak Performing Arts Center, The Record Company); an admin can set those by hand. 18 had no SeatGeek listing, mostly small bars and breweries on Eventbrite. No request failed.
- **The venue's events page isn't always a ticket page (found 2026-10-29).** Of the 24 Etix and AXS venues, the saved `events_page` is a single past or upcoming show for The Webster, Colonial Theatre and Nashua Center for the Arts, a booking request form for Ottobar, and an archive of past shows for Sellersville Theater; four have none. Linking SeatGeek events there would send people to the wrong page.
- **Terms:** do SeatGeek's API terms require attribution, or limit caching? The developer docs don't say. Checked before launch.
- **JSON-LD from a single show's page (found in the first real run, 2026-10-29, `logs/fetch_events-seatgeek-2026-10-29.log`; decided the same day).** For three SeatGeek venues the saved JSON-LD is one show's page: Town Ballroom got 1 upcoming event (SeatGeek has 14 concerts), Preserving Underground 1 (18) and Amityville Music Hall 0 (3). But Ardmore Music Hall's JSON-LD is good: 47 upcoming events, with prices, descriptions, support acts and Tixr links, against SeatGeek's 22 concerts. The user chose: SeatGeek replaces JSON-LD only when it has more (see Decisions).
- **First real run (2026-10-29, worktree database only):** 52 venues linked; the 24 with no Ticketmaster or Eventbrite link fetched with `--skip-ai`: 179 events created, none linking to SeatGeek, no problems.
- **Run with show links and the JSON-LD rule (2026-10-29, worktree database only, same log):** 92 of 212 SeatGeek events link to the show's own Etix or AXS page; a sample of 14 were all the right show. Ticket pages were filled in from the venues' sites for Toad's Place, Colonial Theatre, Nashua Center for the Arts, The Met and The Sinclair. Town Ballroom, Preserving Underground and Amityville switched from JSON-LD to SeatGeek; Ardmore kept its JSON-LD (47 against 22). Reading only the saved events page first gave 41 show pages: those pages are often one show's page, so the homepage is read too. Venues still without show links (Starland Ballroom, Bottlerocket and a few small ones) don't link their shows' pages from their own sites. None of the events links to SeatGeek.
- **Go ahead? Decided 2026-10-29: yes.** The user chose to build the rest, and a new ticket-page field for the links.
- **Bulk venues file? Decided 2026-10-29: no.** The coverage run searched 82 venues in about two minutes with no failures, so `match_seatgeek_venues` searches per venue, like Ticketmaster's. The bulk file would mean S3 downloads in a different schema for no gain at this size.
