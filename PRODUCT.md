# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, served equally:

- **Music fans in the Northeast US** deciding which shows to see, usually this week and near them. They browse the calendar by date, filter it by region, state, town or neighborhood, sort or label shows by distance from where they are, save shows, and subscribe to calendar feeds.
- **Musicians, local and touring,** looking for places to play. They need each venue's facts: whether it takes bookings and how (booking type, booking link, notes), open mics, size, age policy, accessibility, and its upcoming shows as evidence of what it books.

Behind both are **editors**: the people who keep the venue list in a Google Sheet and review events in the Django admin before they're published.

## Product Purpose

A Northeast US music venue database and event calendar. Venues come from a Google Sheet that editors curate; their upcoming shows are fetched from venue websites, ticketing platforms (Ticketmaster, Eventbrite) and AI extraction, then reviewed and approved by editors. Success is a fan finding a show they'd otherwise have missed, at a room they didn't know, and a musician finding a venue that books acts like theirs.

## Positioning

- **Small and DIY venues,** not only ticketed rooms: the bars, cafes, breweries, community and DIY spaces that the big show apps miss.
- **Editor-curated venues:** a list kept by people who know the scene, not scraped listings.
- **Venue facts for musicians** alongside the shows: booking details, open booking, open mics.
- **Near you, by neighborhood:** distance from the visitor and neighborhood filters across the whole region, not one city.

## Operating Context

- Started as a fork of [nyc noise](https://nyc-noise.com/), an NYC music calendar; the schema and scope have diverged on purpose.
- Live at newenglandmusic.onrender.com (Render), deployed from `main`. Not yet shared publicly: it stays unshared until the Google Places map-display terms are settled.
- Data pipeline runs as scheduled jobs (`bin/daily.sh`, `bin/weekly.sh`); editors work in the Django admin (event approval, venue fixes, Places review, artist and band records).
- Artist and band records (admin-only for now) are imported from a sheet or CSV, or made from events' artist names, and enriched from MusicBrainz and Wikipedia.

## Capabilities and Constraints

- **Calendar:** events by date, with geo filters (region, state, metro, town, neighborhood), distance labels from a visitor's location (Census gazetteer), saved shows, calendar feeds, search.
- **Per-event play buttons** from Spotify, Apple Music and YouTube, each bound by its provider's terms (only IDs kept; matches settled on evidence).
- **Third-party data terms constrain what may be shown or stored:**
  - Google Places: only the place ID and 30 days of coordinates may be stored; how a Google map may be displayed is still being settled.
  - Last.fm: nothing from it may be shown or stored.
  - Wikipedia text: shown word for word, credited with a link to the article and CC BY-SA 4.0.
  - MusicBrainz genre tags: credited (CC BY-NC-SA).
  - OpenStreetMap neighborhoods: credited "© OpenStreetMap contributors".
  - Bandcamp: links only; no data, no scraping.
- **Not yet public:** artist and band pages, and showing an event's linked performers to visitors.
- **Undecided:** the site's name (see Brand Commitments).

## Brand Commitments

- **Name:** "New England Music", set by the `SITE_NAME` setting. It isn't final: the site covers the wider Northeast, beyond New England.
- **Non-commercial:** a community resource, with no ads or paid placement. This is also what several data licences require (MusicBrainz's supplementary data, Last.fm's terms).

## Evidence on Hand

- The venue sheet: about 730 venues across the Northeast, with booking, access and safety fields.
- Thousands of fetched events (about 3,000 locally), reviewed in the admin.
- Artist and band records with MusicBrainz data, members and Wikipedia introductions (local; production is still empty).
- No testimonials, user counts, press or partnerships exist; future work must not invent them.

## Product Principles

1. **Both audiences, one dataset.** Every venue fact serves the fan deciding where to go and the musician deciding where to play; neither is an afterthought.
2. **Local first.** Small and DIY rooms get the same standing as big ticketed venues.
3. **Curated over scraped.** Editors approve what's published; automation proposes, people decide.
4. **Honest about sources.** Show only what each data source's terms allow, and credit it where it's shown.
5. **A resource, not a business.** No ads, no paid placement, nothing that trades the visitor's attention for revenue.
