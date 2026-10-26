## Why

`sync_venues_from_gsheets` reads the venue sheet through the `gog` CLI. gog signs in to Google as the user through a browser, so it can't run on Render, and the venue sync can't run as a scheduled job. This is the first of the three blockers listed in `PRODUCTION.md`. The user chose a Google Cloud service account over a published CSV link, so the sheet stays private.

## What Changes

- **The sync can read the sheet with a service account.**
  - **Credentials:** when `GOOGLE_SERVICE_ACCOUNT_JSON` is set, the sync reads both tabs (`V3 - Flattened` and `geo-filters_json`) through the Google Sheets API, signed in as the service account. The variable holds the account's JSON key. It's kept as a host secret, and never committed or logged.
  - **Access:** the account is read-only (the `spreadsheets.readonly` scope), and it can only read sheets that are shared with its email address.
- **gog stays for local use.** Without `GOOGLE_SERVICE_ACCOUNT_JSON`, the sync uses gog exactly as it does today.
- **Nothing downstream changes.** Both readers return the same rows, so venue parsing, area parsing, the dry run and the all-or-nothing transaction are untouched.
- **Errors name the tab and the problem**, such as "the sheet isn't shared with the service account" or "no such tab", but never the key or a token.
- **Docs:** `PRODUCTION.md` gains the one-time setup steps, and `.env.example` and `render.yaml` gain `GOOGLE_SERVICE_ACCOUNT_JSON`.
- **Not in this change:** the Render cron job that runs the sync on a schedule. It's a follow-up, once all three blockers are fixed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `venue-sheet-sync`: the sheet can also be read with a Google service account, chosen by an environment variable, with the same rows as gog and errors that never expose credentials.

## Impact

- **Changed code:** `core/management/commands/sync_venues_from_gsheets.py`. `get_rows_from_google_sheets` picks a reader, and a new `core/google_sheets.py` holds the service-account reader.
- **Dependencies:** `google-auth`, pinned in `requirements.txt` and installed with `uv pip install`. The API call itself uses the `requests` the project already has. `google-api-python-client` isn't needed.
- **Setup, once, by the user:**
  - Create a service account in Google Cloud and enable the Sheets API.
  - Share the sheet copy with the account's email as Viewer.
  - Store its JSON key as a Render secret.
- **Cost:** none. The Sheets API is free at this volume: two reads per sync.
- **Not breaking:** local runs without the variable behave exactly as before.
