## Context

- **What the check produces:** `check_event_sources` builds one dict per venue in `check_venue_unsafe`, with keys `sheet_id`, `name`, `state`, `city_town`, `url`, `events_page`, `best_source`, `json_ld_events`, `ical_url`, `ical_events`, `platforms` (`;`-joined), `js_heavy` (`"yes"` or `""`) and `error`. `handle()` then rewrites the whole `--output` file, even after a `--state` or `--limit` run.
- **What the readers use:**
  - `fetch_events.select_targets` reads `sheet_id`, `best_source`, `json_ld_events`, `events_page`, `js_heavy`, `url` and `ical_url`, the last three through `make_target`.
  - `match_ticketmaster_venues.ticketmaster_sheet_ids` reads `sheet_id` and `platforms`.
  - No reader uses `name`, `state` or `city_town`, which only copy the venue, or `ical_events` and `error`, which are for people reading the report.
- **Existing data:** the local `event_sources.csv` (in `.git/info/exclude`) holds 696 checked venues.
- **On Render:** see proposal.md, Why.

## Goals / Non-Goals

**Goals:**
- The cron jobs share their results through Postgres alone.
- The three commands keep their output and options, apart from the report path.

**Non-Goals:**
- **The cron jobs themselves:** adding them to `render.yaml` is a follow-up, once all three blockers are fixed.
- **A history of checks:** each venue keeps only its latest result.
- **Admin screens:** the results stay internal. The CSV export covers reviewing them.

## Decisions

### A one-to-one `VenueEventSource` model, not new fields on `Venue`

```python
class VenueEventSource(models.Model):
    venue = models.OneToOneField(Venue, on_delete=models.CASCADE, related_name="event_source")
    checked_at = models.DateTimeField()
    url = models.URLField(max_length=1000, blank=True, default="")
    events_page = models.URLField(max_length=1000, blank=True, default="")
    best_source = models.CharField(max_length=32, choices=BestSource.choices)
    json_ld_events = models.PositiveIntegerField(default=0)
    ical_url = models.URLField(max_length=1000, blank=True, default="")
    ical_events = models.PositiveIntegerField(null=True, blank=True)
    platforms = ArrayField(models.CharField(max_length=64), blank=True, default=list)
    js_heavy = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")
```

- **`BestSource` choices:** ical, json-ld, ticketing, ai-extraction, no-website, social-only, robots-blocked, dead-domain, bot-blocked, unreachable and check-failed. These are the values the check already produces.
- **Platforms** become an array, and the JavaScript flag a boolean. The CSV adapter converts them both ways (`;`-joined and `"yes"`/`""`).
- **Why a separate table:** it keeps the crawler's output out of `Venue`.
  - The sheet sync, the places lookup and the Ticketmaster link each own some `Venue` fields. A separate table means one writer per table.
  - Saving a result never touches `Venue`, so `Venue.save()` never runs and doesn't re-render the venue's events.
  - The results are written with `update_or_create(venue=...)` on this model. That doesn't call `Venue.save()`, so no `queryset.update()` workaround is needed.
- *Alternative:* columns on `Venue`. Rejected: it mixes crawler state into the sheet-synced model and invites a `Venue.save()`.
- *Alternative:* keep the CSV and put it on a Render disk or in object storage. Rejected: the user chose the database. A disk can't be shared with cron jobs, and object storage adds a new service.

### `check_event_sources` saves its results in one transaction at the end

- The check gathers results in the thread pool as it does now.
- `handle()` then saves them in one `transaction.atomic()` block.
- A crash halfway through the crawl leaves the previous run's results untouched, never a mix of old and new.

A shared helper, `save_event_source(venue, result)`, turns one result dict into model fields, and the CSV import uses it too.

`--output` is replaced by `--csv <path>`, which is optional. With it, the results from this run are also written with the old column order, through `event_source_csv_row(source)`. The default `event_sources.csv` path is dropped, so a server run writes no file.

### Readers query the model and keep their row shape

To keep the change small, `fetch_events.select_targets` builds its row dicts from the model through one adapter, `event_source_row(source)`. It's the inverse of the CSV mapping, so the pilot selection, `make_target` and the Ticketmaster override keep their current code.

`match_ticketmaster_venues` filters with `VenueEventSource.objects.filter(platforms__contains=["ticketmaster"])`.

The "run the source check first" error fires when `VenueEventSource.objects.exists()` is false:
- **`fetch_events`:** always.
- **`match_ticketmaster_venues`:** only for its default selection.

A venue with no row is skipped as unusable, which is what happens today to a venue missing from the CSV. Linked venues are still added as Ticketmaster targets.

`--report` is removed from both commands. A stale cron entry that still passes it fails loudly with "unrecognized arguments", rather than silently reading nothing.

### A one-time `import_event_sources <path>` command

- **What it does:** reads the old CSV with the same adapter and saves each row through `save_event_source`, matching venues by `sheet_id`.
- **Check time:** results are stamped with the file's modification time, so a later re-check shows as newer.
- **Options:** `--dry-run` reports what would be created, replaced and skipped.
- **Where it runs:** locally against the existing file, before the database is copied to Render. It's also usable on the server if a CSV is uploaded.

## Testing

No test reaches the network:
- **Venue websites:** tests patch `check_venue` (as `test_check_event_sources.py` already does) to return canned result dicts. The crawler itself stays as it is, and its current tests keep mocking `requests`.
- **Ticketmaster:** `TicketmasterClient` is mocked as in `test_match_ticketmaster_venues.py`.
- **Scrapy and Anthropic:** `fetch_events` tests keep their existing mocks.

Tests now create `VenueEventSource` rows instead of writing a CSV to a temporary directory. The helpers `report_row` and `write_report` become `make_source(...)`.

## Risks / Trade-offs

- **[A failed crawl overwrites a good result]**
  - Example: a site is unreachable for a night, and the venue's ical result becomes unreachable.
  - This is the same as today's file. Re-checks are weekly, and a venue linked to Ticketmaster is still fetched.
  - Keeping the last good source is a possible follow-up.
- **[Scripts that call `--report` or `--output` break]** → the docstrings and `PRODUCTION.md` are updated in the same change. Nothing on a server uses them yet.
- **[The import runs against the wrong file]** → `--dry-run` first, and the import reports its counts.

## Migration Plan

1. Add the model and its migration.
2. Locally, run `import_event_sources event_sources.csv --dry-run`, then a real run, logged to `logs/`.
3. Make a fresh database dump, so the Render database starts with the imported results (see `PRODUCTION.md`, Loading the local database).
4. Rollback: revert the commit and the migration. The CSV still works with the old code.
