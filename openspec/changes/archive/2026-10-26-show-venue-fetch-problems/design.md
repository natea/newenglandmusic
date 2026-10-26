## Context

- **How the fetch collects notes:** `fetch_events` collects notes per venue in `notes_by_venue`, keyed by sheet ID, as plain strings. Problems are the notes starting `failed:` (a page that didn't load), `ticketmaster failed:` and `ai extraction failed:`. The rest are informational: truncated pages, events hidden as not music, unlabelled events, and removed iCal duplicates.
- **What it counts:** `save_and_report` has each target's found, upcoming and saved counts, but keeps them only long enough to print them.
- **Job runs:** `record-job-runs` adds `JobRun` and the `RecordedCommand` mixin, which stores `self.job_summary`. This change extends both, so it ships after that one.

## Goals / Non-Goals

**Goals:**
- From the job run page and the venue list, an admin can see in one glance which venues failed, and why.
- No change to what the fetch imports or prints.

**Non-Goals:**
- **Problems from other commands,** for example `match_ticketmaster_venues` failures or `check_event_sources` blocked sites. The same `job_problems` hook can carry them later.
- **Fixing the causes.** Re-linking a venue to Ticketmaster, retrying, or changing its source stays a manual step.
- **History per venue.** A venue keeps only its latest fetch. The job runs hold the history, for 90 days.

## Decisions

**Problems are worked out from the notes the fetch already writes.** A helper `is_problem(note)` checks the three prefixes. This keeps the printed report exactly as it is. The alternative, rewriting every note call into problem and info objects, touches far more code for the same result. A test pins the three prefixes, so a new failure note that doesn't use them shows up there.

**A separate `VenueFetchStatus` model, one-to-one with `Venue`:**
- **Fields:** `fetched_at`, `source`, `found`, `upcoming`, `problems` (a JSON list of strings), and `job_run` (a nullable FK to `JobRun`, `SET_NULL`, so pruning old runs doesn't delete statuses).
- **Why not on `Venue`:** for the same reason as `VenueEventSource`. Saving it never calls `Venue.save()`, which would re-render the venue's events, and each table has one writer.
- **Why not on `VenueEventSource`:** that table holds the source check's result. A venue linked to Ticketmaster can be fetched without ever being checked, so it would have no row.
- **How it's written:** with `update_or_create` per fetched venue, in one transaction at the end of `save_and_report`, and skipped for dry runs.

**`JobRun.problems` is a JSON list:** `[{"venue_id", "sheet_id", "name", "problems": [...]}]`. `RecordedCommand` saves `self.job_problems` alongside `self.job_summary`. Storing the venue's ID makes the admin links work; the sheet ID and name are kept too, so the list still reads correctly if a venue is later deleted.

**The admin pages:**
- **`JobRunAdmin`:**
  - a "problems" read-only field, placed before the output: a red-headed table with one row per venue, linking to `/admin/core/venue/<id>/change/`, with its problems as a list
  - a "problems" list column, showing the count, in red when it's above zero
- **`VenueAdmin`:**
  - **list column:** a "last fetch" column built from the status: "problems (2)" in red, "nothing found" in grey, "OK · 9 upcoming" in green, or "never fetched".
  - **filter:** a `SimpleListFilter` for the four states, built from `fetch_status__problems` (whether the list is empty), `fetch_status__upcoming` and `fetch_status__isnull`.
  - **venue page:** a read-only "Event fetching" section, showing the fetch time, source, counts, problems and the job run link.
  - **query cost:** the venue list uses `select_related("fetch_status")`.

**Testing and external services.** No new external calls. The `fetch_events` tests keep their existing mocks: the fake crawler, `TicketmasterClient` and the mocked AI client. They return canned failures, which the tests then check on the job run and on the venues' statuses. The admin tests use the test client with rows made in the test. The suite still runs with outbound network blocked.

## Risks / Trade-offs

- [A new kind of failure note doesn't match the prefixes, so it's missed.] → The prefix test, and the convention that every failure note starts with `failed` (stated in the helper's docstring).
- [A venue that fails once looks broken until the next fetch.] → That's intended. The status shows the latest fetch, with its time.
- [Large problem lists make big rows.] → At most one entry per selected venue. Messages are already cut to 200 characters by the fetch.

## Migration Plan

One additive migration, after `record-job-runs`' migration. Statuses fill in with the first fetch after the deploy, and venues show "never fetched" until then.

**Rollback:** revert. The new table and column can stay.
