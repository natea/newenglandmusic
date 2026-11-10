Issue: [#14 Create an Export to CSV/Excel option for the venue database](https://github.com/natea/newenglandmusic/issues/14)

# Design

## Context

- **The venue list:** `VenueAdmin` (`core/admin.py`) lists venues with filters (including geo-area, fetch status and place-lookup filters) and search. Its change-list template is `core/templates/admin/core/change_list.html`, which applies to every core model, so the venue button needs its own `admin/core/venue/change_list.html` extending it.
- **Who is staff:** the "admin" group (`core/admin_group.py`) holds every permission on core's models, so its members have `core.view_venue`. Superusers have it too. Django's `has_view_permission` is the natural gate.
- **The data:** `Venue` (`core/models.py`) holds the sheet fields, the Google place fields, the neighborhood and the event-source IDs. `VenueEventSource` is a one-to-one table of the last event-source check.
- **Google's terms** (see `venue-place-lookup`): only the place ID may be stored indefinitely, and the coordinates for 30 days. `place_distance_km` is derived from them and deleted with them. The export treats all of these as not ours to hand out, since a file outlives the 30 days.
- **Not from Google:** the neighborhood is from OpenStreetMap, which allows reuse with credit, so the file includes it and the source column says where it came from.

## Goals / Non-Goals

**Goals:**
- Staff get the venue list, with its filters applied, as a file that opens in Excel or Sheets.
- Nothing is in the file that Google's terms keep out of it.

**Non-Goals:**
- A public export for visitors. The issue calls it a possible low-priority later addition. It would need its own proposal, since it would change who can see safety notes, internal IDs and review state.
- Excel `.xlsx` files. CSV opens in Excel and needs no new package.
- Exporting events, artists or bands, or importing a CSV back in. The sheet stays the master list for venues.
- Scheduled or emailed exports.

## Decisions

**A button on the venue list that exports what the list shows, not an admin action.**
- An admin action needs rows ticked first, or Django's "select all N" step, which is easy to miss. The issue asks for a straightforward way, and a button needs no setup for "everything".
- The button is a custom admin URL (`export-csv/`, wrapped in `admin_site.admin_view`) that takes the list's own query string. It builds the same queryset the list uses with `get_changelist_instance`, so search, filters and ordering match exactly, then ignores pagination.
- The button keeps the current query string, so the filters carry over.
- **Alternative:** an action on selected rows. Rejected as the only way, but could be added later cheaply since both share the row-building code.

**Permission is `has_view_permission`.** The view checks it and answers 403 when it fails. `admin_view` already sends signed-out and non-staff users to the login page. The template shows the button only when `has_view_permission` is true.

**Rows are built in a small module (`core/venue_export.py`), apart from the view.** It owns the column list, the value formatting and the formula guard, so tests can check them without a request.
- **Columns:** an explicit list, not "every model field". A new `Venue` field is then not exported by accident, which matters because a new Google-derived field would otherwise leak. A test fails if a Venue field is neither exported nor on a short, named exclusion list, so adding a field forces a decision.
- **Flags** are "yes", "no" or blank for unknown. Choice fields export their stored value, so the file round-trips with the sheet's vocabulary. Genres join with `; ` as the sheet does.
- **Event source** columns come from `select_related("event_source")`, blank when absent.
- **Excluded:** `place_latitude`, `place_longitude`, `place_distance_km` and `place_looked_up_at`. `exact_location` is not used as a column, since it can return Google's coordinates.
- **Formula guard:** text cells that start with `=`, `+`, `-`, `@`, tab or carriage return get a leading apostrophe. Plain numbers (the sheet coordinates) are written as numbers, so a negative longitude isn't altered. A hyphen-leading text value does get the apostrophe, which is a small, accepted change to that cell.
- **Encoding:** UTF-8 with a byte order mark, as Excel needs it to read accents. Python's `csv` writer handles quoting.

**Streaming.** The venue table is a few thousand rows at most, so the view builds the response with `StreamingHttpResponse` over `queryset.iterator()` only to avoid holding it all at once; nothing needs to be cached. The filename is `venues-YYYY-MM-DD.csv`.

**No audit trail** beyond the web server's request log. The export reads data staff can already see on screen.

## Mocking external services in tests

The export calls no outside service, so there is nothing to mock. Tests create `Venue` and `VenueEventSource` rows directly and use Django's test client with staff, superuser and plain users. Google data is test rows with place fields set. The suite still runs with the network blocked, as the project requires.

## Risks / Trade-offs

- **A later Google-derived field leaks into the file** → the explicit column list and the field-coverage test.
- **A spreadsheet formula injected through a venue's text** (the sheet is edited by others) → the formula guard, tested.
- **Safety notes and internal IDs in the file** → only staff with view permission, who can already read them in the admin.
- **A very large filtered list is slow** → streaming; the table is small enough that this is not a concern today.

## Open Questions

- **Public export:** the issue says it may be wanted later. If so, it needs its own proposal, with a smaller column set and a view of Google's terms for sharing.
- **Event source columns:** the thread said "all the details the site holds". This design includes the last event-source check but not per-venue event counts or fetch status. If wanted, they can be added as columns without changing the approach.
