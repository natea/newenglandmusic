## 1. Service-account reader

- [x] 1.1 Add `google-auth` to `requirements.txt`, pinned to its current release, and install it with `uv pip install -r requirements.txt`. Verify that `python -c "import google.oauth2.service_account"` works.
- [x] 1.2 Create `core/google_sheets.py` with `read_values(sheet_id, a1_range)`:
  - parse `GOOGLE_SERVICE_ACCOUNT_JSON` into credentials with the read-only scope
  - make one `AuthorizedSession` GET to the Sheets API `values` endpoint, with the range URL-encoded and `FORMATTED_VALUE`
  - return the `values` list
  - raise `CommandError`s that name the tab, as described in design.md: invalid key, not shared (naming `client_email`), missing tab, other statuses

  Verify with the tests in 1.4.
- [x] 1.3 Change `get_rows_from_google_sheets` to use `read_values` when `GOOGLE_SERVICE_ACCOUNT_JSON` is set, and gog otherwise. Both readers share the header and padding code. Update the module docstring to say how the sheet is read. Verify with the tests in 1.4 and the existing `GetRowsTestCase`.
- [x] 1.4 Write `core/tests/test_google_sheets.py`, patching `Credentials.from_service_account_info` and `AuthorizedSession.get` (no network). Verify the tests pass. They cover every scenario of:
  - **"The sheet can be read with a Google service account":**
    - service account configured: the read-only scope is used and `subprocess.run` isn't called
    - no service account: gog is used
    - same rows either way: identical parsed rows from gog output and from the API response for the `geo_filters.json` fixture
  - **"Sheet read errors never expose credentials":**
    - invalid key, not shared with the account, missing tab (in a full sync run, neither venues nor areas change)
    - nothing secret in the output, using a fake key with a recognizable `private_key` and a fake token

## 2. Docs and configuration

- [x] 2.1 Add `GOOGLE_SERVICE_ACCOUNT_JSON` to `.env.example`, commented out, with a note that gog is used when it's blank. Verify by reading the file.
- [x] 2.2 Add `GOOGLE_SERVICE_ACCOUNT_JSON` to `render.yaml` as `sync: false`. Verify that `render.yaml` still parses as YAML.
- [x] 2.3 In `PRODUCTION.md`:
  - replace the first blocker with the one-time setup: create a service account in Google Cloud, enable the Sheets API, create a JSON key, share the sheet copy with the account's email as Viewer, and paste the key JSON into Render as `GOOGLE_SERVICE_ACCOUNT_JSON`
  - say how to check the setup: `python manage.py sync_venues_from_gsheets --dry-run` from the Shell tab

  Verify by reading the section.

## 3. Check

- [x] 3.1 Run the full suite with outbound network blocked, and verify that it passes.
- [x] 3.2 After the user has set up the service account, run `sync_venues_from_gsheets --dry-run` with `GOOGLE_SERVICE_ACCOUNT_JSON` set locally, logged to `logs/sync_venues_from_gsheets-YYYY-MM-DD.log`. Verify that the counts match a gog dry run: 729 venues and 53 areas, with no changes. (2026-10-26: both read 729 venues with 0 created and 0 area changes, and the log holds no key or token. The first try found the Sheets API disabled in the Cloud project, which now has its own error message.)
- [x] 3.3 Note the follow-up in `PRODUCTION.md`: a Render cron job for the daily sync, once all three blockers are fixed. Verify by reading the note.
