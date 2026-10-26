## Context

- `get_rows_from_google_sheets(sheet_id, tab)` in `sync_venues_from_gsheets` is the only place the sheet is read. It runs `gog sheets get <id> '<tab>'!A1:ZZ --json --results-only`, then turns the values (a list of rows) into dicts keyed by the header row, padding short rows.
- **Both tabs go through it:** the venue tab, and `geo-filters_json` for areas.
- **Tests:** they mock either it or `subprocess.run`.
- **The constraint:** gog's OAuth sign-in needs a browser, so it can't run on Render. See proposal.md.

## Goals / Non-Goals

**Goals:**
- The sync runs unattended on a server, using only environment variables.
- Local development keeps working with gog and no new setup.

**Non-Goals:**
- **Scheduling:** the Render cron job is a follow-up, after the other two blockers in `PRODUCTION.md`.
- **Writing to the sheet:** the account only reads.
- **The original sheet:** the account is shared on the copy only.

## Decisions

### Credentials come from a `GOOGLE_SERVICE_ACCOUNT_JSON` variable holding the key JSON

The whole key file's JSON goes in one environment variable, set as a secret in Render's dashboard (`sync: false` in `render.yaml`). It's parsed with `json.loads` and given to `google.oauth2.service_account.Credentials.from_service_account_info` with the `https://www.googleapis.com/auth/spreadsheets.readonly` scope.

*Alternative:* a path to a key file (`GOOGLE_APPLICATION_CREDENTIALS`). That's rejected because Render would need a secret file mounted, and a variable is simpler on both Render and a local machine. A local `.env` can still hold it, but locally gog is the default.

### `google-auth` plus the `requests` we already have, not `google-api-python-client`

- **The call:** one Sheets API call per tab, `GET https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}`, with `valueRenderOption=FORMATTED_VALUE` (the same as gog's default output).
- **How:** it's made through `google.auth.transport.requests.AuthorizedSession`, which signs in and refreshes the token itself.
- **The dependency:** only `google-auth`, which brings `cachetools`, `pyasn1-modules` and `rsa`. It's pinned in `requirements.txt` and installed with `uv pip install`.
- **Alternative:** the full client library. It's rejected as a large dependency for a single endpoint.

The range is quoted the way gog's is (`'<tab>'!A1:ZZ`) and URL-encoded, so tab names with spaces work.

### The reader is picked by whether the variable is set

`get_rows_from_google_sheets` keeps its signature and its output:
- If `GOOGLE_SERVICE_ACCOUNT_JSON` is set, it calls `core.google_sheets.read_values(sheet_id, range)`.
- If not, it uses the existing gog call.

Both produce the raw `values` list, and the shared code turns that into dicts. The padding logic therefore exists once, and venue and area parsing can't tell the two readers apart.

*Alternative:* a `--reader` flag. That's rejected because the host's settings decide this, not the person running the command.

### Errors are built from status codes, never from Google's response or the key

`read_values` raises `CommandError`s that name the tab:
- **The key doesn't parse or isn't a service-account key:** "GOOGLE_SERVICE_ACCOUNT_JSON isn't a valid service-account key". The value is never echoed.
- **403, or 404 on the spreadsheet:** "can't read tab 'X': share the sheet with <client_email> as a Viewer". The `client_email` field isn't secret, and it's exactly what the user needs.
- **400 "Unable to parse range":** "tab 'X' doesn't exist".
- **Anything else:** the tab, the HTTP status and Google's `error.message`, cut to 200 characters. Google's messages don't contain tokens, but the request headers, which do, are never printed.

Exceptions from `google-auth` are caught and re-raised without their arguments, because a refresh error can include the token response.

## Testing

No test touches the network.
- **Google:**
  - **`Credentials.from_service_account_info`** is patched to return a stub, so no real key, and no RSA signing, is needed.
  - **`AuthorizedSession.get`** is patched to return canned responses: a 200 with `values`, a 403, a 404, and a 400 "Unable to parse range".
  - **Fixture:** the canned 200 body reuses `core/tests/fixtures/geo_filters.json`, wrapped as `{"range": ..., "values": [...]}`.
- **The no-secrets scenario:** it uses a fake key JSON with a recognizable `private_key` string and a fake token. The test checks that neither appears in the command's output or in the exception.
- **gog fallback:** covered by the existing `GetRowsTestCase` with the variable unset, plus one test that `subprocess.run` isn't called when the variable is set.
- **Both readers:** one test feeds the same values to each and compares the parsed rows.

## Risks / Trade-offs

- **[The key leaks]**
  - **Mitigation:** the account can only read, and only sheets shared with it, which is the copy alone. The key lives only in Render's secrets.
  - **Recovery:** if it leaks, delete the key in Google Cloud and create a new one.
- **[The sheet is shared with a new address]** The copy gains one Viewer: the service account. It still isn't public, which is what the user asked for.
- **[gog and the API format values differently]** Both default to formatted values, and the sync already strips and parses every cell. The "same rows either way" test pins this down.

## Migration Plan

1. Add the dependency and the code. Locally, nothing changes without the variable.
2. The user creates the service account, enables the Sheets API, shares the sheet copy and sets the secret on Render. These steps go in `PRODUCTION.md`.
3. Run `sync_venues_from_gsheets --dry-run` from Render's Shell tab to confirm.

Rollback: unset the variable, and the sync goes back to gog.
