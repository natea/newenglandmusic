Issue: [#151 Remove the inherited data-export endpoint and its settings](https://github.com/natea/newenglandmusic/issues/151)

## 1. Remove the endpoint and command

- [ ] 1.1 Remove the `internal-api/db` path and the `internal_db_dump` import from `core/urls.py`
- [ ] 1.2 Delete `core/views/internal_db_dump.py`
- [ ] 1.3 Delete `core/management/commands/populate_data_from_prod.py`
- [ ] 1.4 Add tests: `/internal-api/db` answers 404 with a bearer token, with `unused`, and with no header; `internal_db_dump` no longer reverses; `populate_data_from_prod` is an unknown command

## 2. Remove the settings and where they are set

- [ ] 2.1 Remove `RC_DEVELOPER_INTERNAL_TOKEN` and `PROD_INTERNAL_API_SERVER` from `nycnoise/settings/base.py`
- [ ] 2.2 Remove both from the four env lists in `render.yaml` and the comment above them
- [ ] 2.3 Remove both from `.env.example`, `.github/workflows/django.yml`, and the `test.env` in `.fabro/workflows/build/workflow.fabro`
- [ ] 2.4 Remove the table row in `PRODUCTION.md` and any other doc mention
- [ ] 2.5 Add tests: settings load with both variables unset and define neither; no config or doc file mentions either name or keeps a fixed token

## 3. Verify

- [ ] 3.1 Run `venv/bin/python manage.py test` with neither variable in the environment, and with outbound network blocked
- [ ] 3.2 After deploy, check that `/internal-api/db` answers 404 and that Render's dashboard no longer lists the two variables (delete them by hand if they remain)
