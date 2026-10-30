---
name: New England Music
description: A dense, text-first calendar of Northeast US live music, on warm grey paper, with each act filed as an index card.
colors:
  ground: "#d4d0c7"
  card-stock: "#f6f4ee"
  hairline: "#b9b4a8"
  plum: "#8b5b8b"
  lavender-strip: "#eeeeff"
  ruled-blue: "#c9d3e6"
  navy-link: "#000080"
  ink: "#000000"
  card-ink: "#1a1a1a"
  quiet: "#4f4b44"
  divider: "rgba(0, 0, 0, 0.3)"
  teal-aside: "#008080"
  tix-yellow: "rgba(255, 255, 59, 0.8)"
  today-cream: "rgb(251, 247, 224)"
  grid-line: "#dddddd"
  muted: "#999999"
  paper-white: "#ffffff"
  gcal-blue: "#1a73e8"
  map-plum: "#993366"
typography:
  display:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "clamp(2rem, 7vw, 3.4rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "2em"
    fontWeight: 700
  calendar-date:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
  title:
    fontFamily: "Helvetica, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
  body:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "1rem"
    fontWeight: 400
  body-lead:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.4
  body-ruled:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: "28px"
  label:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
  small:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
  caption:
    fontFamily: "\"Open Sans\", sans-serif"
    fontSize: "0.82rem"
    fontWeight: 400
rounded:
  none: "0px"
  icon: "4px"
  embed: "10px"
  pill: "12px"
  pill-lg: "14px"
spacing:
  hair: "2px"
  xs: "4px"
  sm: "6px"
  md: "10px"
  rule-gap: "14px"
  block: "18px"
  card-x: "24px"
  time-column: "4.6em"
  field-column: "7.5em"
components:
  link:
    textColor: "{colors.navy-link}"
  month-bar:
    backgroundColor: "{colors.plum}"
    textColor: "{colors.paper-white}"
    padding: "1px 6px 2px"
  filter-strip:
    backgroundColor: "{colors.lavender-strip}"
    textColor: "{colors.ink}"
    padding: "6px"
  day-header:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
    padding: "10px 0 5px"
  event-row:
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    padding: "10px 0"
  action-icon:
    textColor: "{colors.ink}"
    rounded: "{rounded.icon}"
    padding: "2px"
    size: "18px"
  pill:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.small}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  calendar-link:
    backgroundColor: "{colors.paper-white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill-lg}"
    padding: "3px 10px"
  tix-badge:
    backgroundColor: "{colors.tix-yellow}"
    textColor: "{colors.ink}"
    typography: "{typography.small}"
    rounded: "{rounded.none}"
    padding: "0 1px"
  act-tab:
    backgroundColor: "{colors.plum}"
    textColor: "{colors.paper-white}"
    typography: "{typography.display}"
    rounded: "{rounded.none}"
    padding: "0.18em 0.45em 0.12em"
  act-card:
    backgroundColor: "{colors.card-stock}"
    textColor: "{colors.card-ink}"
    rounded: "{rounded.none}"
    padding: "18px 24px 22px"
  act-card-mobile:
    padding: "14px 14px 18px"
  next-show-strip:
    backgroundColor: "{colors.lavender-strip}"
    textColor: "{colors.card-ink}"
    typography: "{typography.body-lead}"
    padding: "10px 14px"
  field-label:
    textColor: "{colors.quiet}"
    typography: "{typography.label}"
    width: "7.5em"
  ruled-bio:
    textColor: "{colors.card-ink}"
    typography: "{typography.body-ruled}"
  headshot:
    backgroundColor: "{colors.ground}"
    rounded: "{rounded.none}"
    size: "48px"
---

# Design System: New England Music

## Overview

**Creative North Star: "The Record-Store Bin"**

New England Music is a long, honest list on warm grey paper: the calendar is the stock, sorted by month and day, and each act is a filed index card with its name printed on a plum divider tab. The look came with the nyc noise fork and is kept on purpose. It is dense, text-first and close to the browser's own defaults: bold sans names, navy underlined links, thin rules between rows, and a few flat colour bands (lavender for the strips you act on, plum for the dividers you navigate by). Nothing is decorative. Every colour band means something, and a sparse local act's card and a famous band's card use the same fields, so both read as the same kind of record.

Density is the point. A listing row is a time column, bold performer and venue names, a small grey description, and a row of 18px line icons, with no cards, thumbnails or spacing to soften it. The band page adds the system's one container, an off-white card on the grey ground, and keeps the same single 42em column, the same navy links, the same lavender strip and the same icon row as the calendar, so moving from a listing to an act feels like pulling one card out of the bin.

**Key Characteristics:**
- One 42em column on warm grey (#d4d0c7), for every page.
- Flat colour bands with fixed meanings: lavender for filtering and the next show, plum for month navigation and the act's tab and rules.
- Navy underlined links in content; bold names (performers, venues, dates) over regular-weight detail.
- Text-first, dense listings with thin divider rules, never boxed cards.
- One container, the act card: off-white stock, a hairline border, a 3px plum top edge, square corners.
- 18px line icons drawn with a 1.8 stroke in currentColor, the only icon language.

## Colors

A warm grey paper palette with two flat accent bands (plum and lavender) and the browser's classic navy link, with no gradients and no tints of the brand colours.

### Primary
- **Divider Plum** (plum): the system's structural colour. It fills the month bar under the calendar, prints the act's name tab, edges the act card's top (3px) and draws the 2px rules between the card's sections. It is always a bar, tab or rule, with white type on it. It is never used for text on grey or for a button fill.

### Secondary
- **Strip Lavender** (lavender-strip): the band the visitor acts on. It holds the region/state/metro filter, the calendar-subscribe drawer, the "no matching events" notice and, on the act card, the next-show strip joined to its action icons. It also tints text selection on the card.
- **Link Navy** (navy-link): every content link, underlined. On the card the underline sits 0.15em below the baseline, and keyboard focus draws a 2px navy outline 2px out.

### Tertiary
- **Ticket Yellow** (tix-yellow): the small "tix" badge at the right of a listing row, boxed with a 1px black border. It is the only saturated fill in a listing.
- **Today Cream** (today-cream): today's cell in the month grid.
- **Aside Teal** (teal-aside): secondary links: "go to top" and venue accessibility notes.
- **Calendar Blue** (gcal-blue) and **Map Plum** (map-plum): the Google Calendar and map icons in the action row, and the Google calendar-feed pill. The other icons inherit their text colour.

### Neutral
- **Paper Grey** (ground): the page ground everywhere. The sticky day header repeats it so rows scroll under it cleanly.
- **Card Stock** (card-stock): the act card's face, the only raised surface.
- **Hairline** (hairline): the act card's 1px border and its 1px bottom edge. It also backs headshots and photos while they load.
- **Ruled Blue** (ruled-blue): the faint lines behind the act's bio and the 1px rules between its show rows.
- **Ink** (ink) and **Card Ink** (card-ink): text on the grey ground, and the slightly softer text on the card.
- **Quiet Grey** (quiet): the card's secondary text: the meta line, field labels, roles, years, captions, credits and the footnote. (Listings use #555 for the same job, on the distance label.)
- **Row Rule** (divider): the 1px rule under each listing row and the 1px border of every pill.
- **Grid Line** (grid-line) and **Muted** (muted): the month grid's cell borders, and the other month's dates.
- **Paper White** (paper-white): type on plum, and the calendar-link pills' face.

### Named Rules
**The Band Means Something Rule.** Lavender marks where the visitor filters or acts (the filter, subscribe drawer, empty notice, next-show strip). Plum marks where they navigate or where a record starts (the month bar, the act tab, the card's section rules). A new surface uses each band for that job only, and never for decoration.

**The Navy Underline Rule.** Content links are navy and underlined. Only the masthead title, the burger and the ticket badge drop the underline.

## Typography

**Display Font:** Helvetica (with Arial, sans-serif), on the act tab and the card's section headings
**Body Font:** "Open Sans" (with sans-serif) for everything else, including the masthead and the day headers

**Character:** one plain, heavy sans voice. Names and headings are bold; detail is regular and smaller. The band page's Helvetica stack matches how the incumbent headings already render, since Open Sans is declared but never loaded, so every page shows the platform's sans.

### Hierarchy
- **Display** (800, clamp(2rem, 7vw, 3.4rem), 1.02, -0.015em): the act's name on the plum tab, and nowhere else.
- **Headline** (700, 2em): the masthead "New England Music" and the sticky, centred day header ("oct 29 (thurs)"), which is a black underlined link.
- **Calendar Date** (700, 1.6rem): the day numbers in the month grid, navy and underlined, lowercase where they are words.
- **Title** (700, 1.25rem): the act card's section headings ("Upcoming shows").
- **Body** (400, 1rem): listing rows and card text. Performers, event titles, venues and dates are bold within it.
- **Body Lead** (400, 1.05rem, 1.4): the card's meta line and next-show strip.
- **Body Ruled** (400, 1rem, 28px line height on 28px rules, 65ch measure): the act's bio.
- **Label** (700, 1rem, 1.5, Quiet Grey): the card's field labels in their 7.5em column. The "Former members" subhead is a 0.92rem version.
- **Small** (400, 0.85rem): event descriptions, prices, distance, pills, the subscribe drawer, the card's footnote.
- **Caption** (400, 0.82rem): photo captions and the bio's licence credit.

### Named Rules
**The Tabular Time Rule.** Times, dates and year ranges use tabular figures: the listing's 4.6em time column, the next-show date, the show list's dates and the members' years. Columns of times line up.

**The Bold Names Rule.** The things a visitor scans for (performers, venues, the show's date) are bold. Everything around them is regular weight. Weight sets the hierarchy, not colour or size.

## Layout

There is one centred column, `main`, at most 42em wide with 15px above and below and 8px of page margin, at every viewport. The masthead row (burger, title, right-aligned header links) sits above it. On the homepage the column holds the lavender filter strip, the month grid (seven equal cells, 1rem vertical padding), the plum month bar, then day sections. Each day has a sticky header (z-index 3, on the grey ground) and a stack of listing rows.

A listing row is a wrapping flex row. The time sits in a fixed 4.6em column, the text fills the rest, and the ticket badge takes a 24px column at the right. Play buttons, players and the action-icon row wrap onto rows of their own, indented 4.6em so they line up with the text. Rows are 10px top and bottom, separated by the 1px row rule.

The act page puts its card in the same column, 22px below the masthead. Inside, the rhythm is 18px between blocks, and each section opens with a 2px plum rule and 14px of space. Field lists and the show list share a two-column grid (7.5em label column, 16px gap). Below 600px, the system's only breakpoint, the card's padding drops to 14px, field labels stack above their values, the show list's date column narrows to 6.5em, and the "more shows" link wraps under the strip. The incumbent calendar has no breakpoints: it narrows with the viewport.

**The One Column Rule.** Every page sits in the 42em column. New surfaces don't widen it or add sidebars; a container lives inside it.

## Elevation & Depth

The system is flat. Depth comes only from colour bands and rules: the sticky day header covers the rows by repeating the ground colour, not with a shadow. The act card's only lift is a hard 1px hairline under it.

### Shadow Vocabulary
- **Card edge** (`box-shadow: 0 1px 0 #b9b4a8`): under the act card only, so it reads as one card of stock sitting in the bin.

**The Flat Paper Rule.** No blurred or offset shadows. A surface separates from the ground by colour, a hairline and a rule.

## Shapes

Containers and bands are square: the act card, its tab, the strips, the month bar, the ticket badge, headshots and photos all have 0 radius. Rounding belongs to small controls only: action icons get a 4px hover plate, play buttons and town chips are 12px pills, calendar-feed links are 14px pills, and embedded players are rounded to 10–12px. Lines do most of the work: 1px row rules, 1px pill borders, 2px plum section rules, a 3px plum card top, and faint 1px blue rules every 28px behind the bio.

## Components

### Links and text actions
- **Style:** navy and underlined in content. On the card, the underline sits 0.15em below the baseline. "More" disclosures ("3 more former members") are a `details` summary styled as a navy underlined link.
- **Focus:** a 2px navy outline, 2px out, on the card.

### Action icon row
The calendar's one icon language, reused on the act page.
- **Style:** 18px line icons (iCal download, Google Calendar, map, share, save), stroke 1.8 in currentColor with round caps and joins, 10px apart, each in a 2px padded hit area.
- **Colour:** inherit ink, except Google Calendar (gcal-blue) and map (map-plum). Save fills solid when saved.
- **Hover:** an 8% black plate with a 4px radius. Each icon is named by its title.

### Pills (play buttons, town chips, calendar-feed links)
- **Style:** transparent with a 1px row-rule border, a 12px radius, 1px 8px padding and small type, with a 12–14px brand mark. Calendar-feed pills are white, 3px 10px, with a 14px radius and a 16px line icon.
- **Hover:** the border takes the service's colour (Spotify green, Apple red, YouTube red, Google blue), or black.

### Ticket badge
- **Style:** "tix" in small type on ticket yellow, a 1px black border, square, no underline, right-aligned in its own 24px column.

### Strips and bars
- **Filter strip:** lavender, 6px padding, labels and selects wrapping with a 4px 12px gap. The subscribe drawer and the empty notice share it.
- **Month bar:** plum, with the previous, current and next months as three equal white links.

### Listing row
- **Structure:** time column (tabular), bold names, venue in bold with its town, a small description after "//", then the wrapped rows of icons and pills. A row that is the URL target flashes orange (#ffa600 fading over 2s, ease-out). A cancelled row is struck through and greyed (#666).

### Act card (signature component)
A record-store divider and index card for one band or artist.
- **Tab:** the act's name in display type, white on plum, sitting flush on the card's 3px plum top edge and as wide as the name needs. Long names wrap anywhere.
- **Card:** card stock, a 1px hairline border, the 1px card-edge shadow, square corners, padding 18px 24px 22px (14px 14px 18px on phones).
- **Meta line:** kind, genres, origin and year in Body Lead and quiet grey, separated by middots.
- **Next-show strip:** the lavender band, with the bold tabular date and time, the venue as a link with its town, and "N more shows" at the right. The show's action icons sit in the same band below it, so the show and its actions read as one block. With no show it says "No upcoming shows listed." in quiet grey.
- **Fields:** a definition list with bold quiet-grey labels in a 7.5em column. Members are a list with roles and years in quiet grey. Square 48px headshots appear only when a member has one, and then every name keeps the same column. There are no placeholder silhouettes. Links are joined by middots.
- **Bio:** on ruled card stock (1px ruled-blue every 28px, text at a 28px line height and 65ch measure), with its licence credit in caption type.
- **Photo:** a field after the bio, at most 480px wide and 26rem tall, with its credit as a caption.
- **Show list:** a Title heading, then a grid of rows with a bold tabular date (the time below it in quiet grey) and the venue with its icon row, separated by 1px ruled-blue rules.
- **Foot:** the invitation to send a photo, bio or links, and the genres' source, in small quiet type.
- Empty fields are left out entirely, so a sparse act's card is short and nothing on it is filler.

## Do's and Don'ts

### Do:
- **Do** keep every surface in the single 42em column on the warm grey ground (#d4d0c7).
- **Do** use lavender (#eeeeff) for the band where a visitor filters or acts, and plum for month navigation, an act's tab and its section rules (2px) and top edge (3px).
- **Do** set content links in navy (#000080) with their underline.
- **Do** make names, venues and dates bold, and set times, dates and years in tabular figures.
- **Do** reuse the 18px line-icon action row (stroke 1.8, currentColor) wherever an event appears.
- **Do** leave a field out when there is no data for it. Never draw a placeholder.
- **Do** keep containers square, and round only small controls (4px icon plates, 12–14px pills).

### Don't:
- **Don't** add blurred or offset shadows. The act card's 1px hairline bottom edge (0 1px 0 #b9b4a8) is the only shadow.
- **Don't** box listing rows into cards. A row is separated by its 1px rule.
- **Don't** use plum or lavender as text colours, button fills or decorative tints.
- **Don't** widen the column or add a sidebar. On an act page the name and next show come first, and a photo is a credited field after the bio, never a banner.
- **Don't** introduce a second icon style (filled, duotone or glyph icons) alongside the line icons.
