## Context

- **The commands:** the five pipeline commands are plain `BaseCommand` subclasses, and they report through `self.stdout.write`. Errors are raised as `CommandError` or as uncaught exceptions.
- **Their options:** each has its own. `--dry-run` exists on `fetch_events`, `match_ticketmaster_venues` and `lookup_venue_places`.
- **Output size:** a full `fetch_events --all` prints roughly 120 KB locally. Most of that is scrapy's own logging on stderr; the per-venue report on stdout is a fraction of it.
- **How they'll run on Render:** as Cron Job services (see `PRODUCTION.md`), each run in a fresh container. The output goes to Render's Logs tab, which keeps it for a limited time.

## Goals / Non-Goals

**Goals:**
- Every run of the five commands leaves a durable, readable record, whether it's run by cron, by hand or by a test.
- Recording never changes what a command does or prints, and never makes a working command fail.

**Non-Goals:**
- **Alerts:** email or chat when a run fails. A natural follow-up, built on these records.
- **Storing stderr:** that's scrapy's and the libraries' logging. It stays in Render's Logs tab, and a log stream can keep it longer.
- **Starting or scheduling jobs from the admin.**
- **Other commands,** such as `classify_events`, `resave_all_events` and `import_event_sources`. They're run by hand, and the mixin makes adding them a one-line change later.

## Decisions

**A `JobRun` model.**
- **Fields:**
  - `command` (the name)
  - `arguments` (JSON: the options given, minus Django's standard ones)
  - `started_at` and `finished_at`
  - `status` (`running`, `succeeded` or `failed`)
  - `dry_run`
  - `summary` (JSON: an ordered list of label and count pairs)
  - `output` (text)
  - `error` (text)
- **Indexes:** on `started_at` and on `command`.
- **"Didn't finish" isn't stored.** It's worked out when a run is shown: `running` and started more than `STALE_AFTER` (6 hours) ago. A killed process can't update its own row, and a later sweep could race with a genuinely long run. Showing it this way is always right.

**A `RecordedCommand` mixin overrides `execute()`.**
- **At the start:** it creates the row.
- **Capturing output:** it replaces `options["stdout"]` with a tee, which writes to the real stream and to a buffer. Django's `OutputWrapper` and `self.style` therefore behave exactly as before, and the output is unchanged.
- **At the end:** on return it saves `succeeded`, the captured output and `self.job_summary`. On an exception it saves `failed`, the traceback and the output so far, then re-raises, so exit codes and `CommandError` messages are unchanged.
- **Why `execute()`:** it's the one entry point that both `manage.py` and `call_command` go through.
- **Alternative considered:** a wrapper script that runs each command and stores its output. Rejected, because it would miss runs started by hand and couldn't see the command's own summary.

**Recording is best-effort.** Each database write in the mixin is wrapped, so if recording fails, a warning goes to stderr and the command carries on. A database problem that would break the command anyway still surfaces as the command's own error.

**Summaries are set by each command.** Each command assigns `self.job_summary = [("events created", n), ...]` from counts it already computes. A command that sets nothing gets an empty summary. The list shows the summary as "events created 12 · updated 340 · venues failed 3".

**A size limit on the stored report.** Output over 200,000 characters keeps the first and last 100,000, with a line in between saying how many characters were left out. That bounds any one row while keeping the start of a run and its final totals.

**Pruning happens on insert.** Creating a run first deletes runs older than 90 days. It's one indexed delete, so it needs no separate scheduled job.

**The admin is read-only.**
- **Permissions:** `has_add_permission` and `has_change_permission` return False, while viewing stays allowed through `has_view_permission`.
- **The list:** columns for command, started, duration, outcome and summary; filters for command and outcome; newest first.
- **Outcome:** shown as a coloured label, with failed and "didn't finish" in red. "Didn't finish" is also a choice in the outcome filter.
- **Each run's page:** shows the output and error in a monospace block.

**Testing and external services.** Recording calls no external service. The tests:
- run the real commands through `call_command`, with their existing mocks: `gog` output for the sheet sync, mocked `requests` for the source check, and mocked `TicketmasterClient`, Places, scrapy and Anthropic for the others. Each run's `JobRun` is then checked.
- force a failure with the missing-API-key paths, which make no requests.
- use a small test-only command class for the output limit, the best-effort path and pruning.

The suite still runs with outbound network blocked.

## Risks / Trade-offs

- [The tee changes output subtly, for example colours or line endings.] → A test compares a command's output with and without recording.
- [A long run holds an open `running` row.] → That's intended, and it's how an in-progress run is shown.
- [Very chatty commands make large rows.] → The 200,000-character limit and 90-day pruning keep this bounded: at a few runs a day, about 10 MB at most.
- [Recording in tests adds rows to every command test.] → Tests run in transactions, so the rows don't persist.

## Migration Plan

One additive migration. Release through `main`. Runs start being recorded with the first scheduled or manual run after the deploy.

**Rollback:** revert. The table can stay.
