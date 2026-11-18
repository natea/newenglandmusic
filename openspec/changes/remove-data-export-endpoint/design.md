Issue: [#151 Remove the inherited data-export endpoint and its settings](https://github.com/natea/newenglandmusic/issues/151)

## Context

`core/urls.py` routes `internal-api/db` to `internal_db_dump`, which checks a bearer token against `settings.RC_DEVELOPER_INTERNAL_TOKEN` and returns `Event.all_objects`, `Venue.objects` and `StaticPage.all_objects` as JSON, plus migration names. `populate_data_from_prod` is the only caller, and it targets `PROD_INTERNAL_API_SERVER` (nyc-noise.com). `nycnoise/settings/base.py` reads both with `os.environ[...]`, so a missing variable stops startup. They are set in `render.yaml` (four places, with the values `https://nyc-noise.com/` and `unused`), `.env.example`, `.github/workflows/django.yml` and the build workflow's `test.env` (`0xdeadbeef`), and noted in `PRODUCTION.md`. A search of the code, tests and specs found no other use and no existing test of the endpoint. Venue export and act export (`venue-export`, `act-export` specs) are separate, admin-side features and are untouched.

## Goals / Non-Goals

**Goals:**
- Delete the endpoint, command and both settings, and every place that sets them.
- `/internal-api/db` answers 404 for any request.
- Startup and tests need neither variable.

**Non-Goals:**
- Replacing the endpoint with any other export.
- Adding a custom 404 handler or a block rule for the old path. Once the route is gone, Django's normal not-found handling answers.
- Changing the admin-side venue or act exports.

## Decisions

- **Delete rather than disable.** Remove the route, view and command outright. A flag or a stub that returns 404 by hand would leave dead code and a setting to explain.
- **Let the missing route produce the 404.** Tests assert the status with a token, without one, and with the former `unused` value, and assert the URL name no longer reverses.
- **Remove the settings, not default them.** Defaults (`os.environ.get`) would keep names nothing reads. With both gone from `base.py`, no environment needs them.
- **Stale values in already-deployed environments are harmless.** Render may keep the old variables set on its dashboard until someone deletes them; nothing reads them. Removing them from `render.yaml` is enough for the blueprint.
- **The fixed token goes away with the setting.** Removing `0xdeadbeef` from the workflow files and test env satisfies "no fixed token kept in the repository" at the change's merge.

## Testing

- No outside service is called by the new tests. Nothing needs mocking: the 404 tests use Django's test client, and the command test uses `call_command`. The removed command's own `requests` call to nyc-noise.com disappears with it, so the suite still passes with outbound network blocked.
- The settings scenario is tested by loading the settings module in a subprocess or via `importlib` with the two variables removed from a copied environment, and asserting no such attributes exist.
- The "no file mentions the settings" scenario is a test that walks the tracked config and docs files (`render.yaml`, `.env.example`, `.github/`, `.fabro/`, `PRODUCTION.md`, `AGENTS.md`, `nycnoise/`, `core/`) and asserts neither name appears. The test file itself must build the names from pieces so it doesn't match its own search.

## Risks / Trade-offs

- **Gap before deploy.** Until this ships, the deployed endpoint accepts the literal token `unused` and exports every event, venue and page. The issue says the token should not be a fixed one until deployment. See the first open question.
- **Local `.env` files.** Developers with the two names in their `.env` see no effect, since nothing reads them.
- **Dropping the 401 behavior.** Callers expecting 401 on a bad token now get 404. There are no known callers other than the removed command.

## Open Questions

- The issue asks that, until this is deployed, the token's value not be a fixed one kept in the repository. The only fixed values are `0xdeadbeef` (test env, removed by this change) and `unused` in `render.yaml` (live on the deployed endpoint). Should the interim step be a separate quick change that sets the Render value to a generated secret (`generateValue: true`) ahead of this one, or is deploying this change promptly enough? This proposal assumes the latter.
