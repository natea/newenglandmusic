# Design

## Context

- The Metro Area menu is a native `<select>` with `<optgroup>`s (`core/templates/core/geo_filter_form.html`), shared by the listing and the discovery deck through `geo_filter_context`. Choosing an option submits the form (or, without JavaScript, the filter button does), so the page always reloads with the metro chosen.
- A native select gives the page no hover events in Chrome or Safari on a desktop, and phones open their own picker. Firefox draws its own list and shows an option's `title` on hover.
- Massachusetts sub-regions match by `cities` (with aliases), Boston's by `neighborhoods`; other metros by `counties` or `cities` (`core/geo_areas.py`).

## Goals / Non-Goals

**Goals:** a visitor who picks a metro sees what it covers; the text reads as the editors wrote it.

**Non-Goals:** a custom dropdown with hover previews (keyboard, screen reader and phone behaviour would have to be rebuilt, and phones still have no hover); listing towns in the option text itself (the menu gets long and hard to scan); showing only towns with venues (the town filter already does that once a metro is chosen).

## Decisions

### 1. A `covers` text per area, in the editors' words
Each Massachusetts sub-region gets `covers` in `core/geo_areas.py`, copied from the editors' list ("Barnstable/Hyannis, Yarmouth, Dennis"; "Back Bay, Beacon Hill, South End, North End, Fenway, Downtown, West End"). `GeoArea` gains a `covers` text field (blank by default), loaded by the existing migrate sync. A metro with no `covers` falls back to its counties ("Cheshire, Hillsborough and Merrimack counties", title-cased) or else its towns, so every offered metro has a text without hand-writing 8 more.
*Alternative:* derive it from `cities`: rejected, as aliases kept for matching would show.

### 2. Shown under the menu for the chosen metro
When a metro is chosen, the form renders `<p class="metro-covers">Covers: …</p>` right after the Metro Area menu, server-side, so it works without JavaScript and on phones. It's plain text, in the filter's muted style, wrapping on a phone.

### 3. A tooltip on each option
Each `<option>` gets `title="Covers: …"`. Cheap progressive enhancement: Firefox shows it on hover; Chrome and Safari ignore it.

## Risks / Trade-offs

- **Most desktop visitors see the towns only after choosing:** the native menu allows no more; switching back is one choice away.
- **The editors' text can drift from the matching lists:** a test checks every town named in `covers` (split on commas and "/") is matched by its sub-region's `cities` or `neighborhoods`.

## Testing

Django `TestCase`s on the rendered form (listing and deck): the covers line for a sub-region, a Boston sub-region, a county-matched metro and no metro; the option `title`s; the data test for `covers` against the matching lists. No external services are involved, so nothing is mocked.
