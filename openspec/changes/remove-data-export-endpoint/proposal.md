Issue: [#151 Remove the inherited data-export endpoint and its settings](https://github.com/natea/newenglandmusic/issues/151)

## Why

The site still carries a data-export endpoint inherited from nycnoise. `/internal-api/db` returns every event (approved or not), venue and static page as JSON to any caller that sends the token `RC_DEVELOPER_INTERNAL_TOKEN`. Its only user is `populate_data_from_prod`, which copies data from nyc-noise.com, not from this site. The schema has diverged on purpose, so the command cannot work here either. Meanwhile the endpoint is a standing way to read the whole database, and the two settings it needs (`RC_DEVELOPER_INTERNAL_TOKEN`, `PROD_INTERNAL_API_SERVER`) are required at startup, so every environment has to invent values for them. The test and build environments use the fixed value `0xdeadbeef`, kept in the repository.

## What Changes

- **BREAKING** Remove the `/internal-api/db` route and its view `core/views/internal_db_dump.py`. A request to that path answers 404 whatever token it sends.
- Remove the `populate_data_from_prod` management command.
- Remove the settings `RC_DEVELOPER_INTERNAL_TOKEN` and `PROD_INTERNAL_API_SERVER` from `nycnoise/settings/base.py`, so the site starts without them.
- Remove every place that sets them: the four env lists in `render.yaml` (web service and three jobs), `.env.example`, `.github/workflows/django.yml`, the build workflow's test environment (`.fabro/workflows/build/workflow.fabro`), and the line about them in `PRODUCTION.md`.
- No `Venue`, `Event` or other model changes, no migrations.

## Capabilities

### New Capabilities
- `site-hardening`: what the site refuses to serve or require. First requirements: no whole-database export route, and no inherited export settings needed to start.

### Modified Capabilities
None. No existing spec in `openspec/specs/` describes the endpoint, the command or the two settings.

## Impact

- Code: `core/urls.py`, `core/views/internal_db_dump.py` (deleted), `core/management/commands/populate_data_from_prod.py` (deleted), `nycnoise/settings/base.py`.
- Config and docs: `render.yaml`, `.env.example`, `.github/workflows/django.yml`, `.fabro/workflows/build/workflow.fabro`, `PRODUCTION.md`.
- Operations: the deployed Render services have `RC_DEVELOPER_INTERNAL_TOKEN` set to the literal `unused`, from `render.yaml`. Until this ships, that is a guessable token on a live endpoint (see the design's open questions). Nothing else uses the endpoint, so removal affects no current feature.
- No screens change, so no design label is needed.
