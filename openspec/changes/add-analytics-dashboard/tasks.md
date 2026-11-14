# Tasks

## 1. Access and the query shape

- [ ] 1.1 Nate creates a PostHog personal API key scoped to project 735651 with `insight:read`, `insight:write`, `dashboard:read` and `dashboard:write`, and puts it in the local `.env` as `POSTHOG_PERSONAL_API_KEY` (never on Render or in chat); verify the command (task 3.1) can list the project's dashboards.
- [ ] 1.2 Build one trend, one breakdown table and one funnel by hand in PostHog, read each back with `GET /api/projects/735651/insights/<id>/`, and record their `query` JSON shapes in `design.md`; verify the helpers in task 3.1 produce the same shapes.

## 2. The new events

- [ ] 2.1 Add `search_results_viewed` (the results card's `data-search-counts`, from the counts the search view already has) and `act_page_viewed` (the act page's `data-act-view`), captured on load by `analytics.js`; verify "A search that finds nothing", "A search's counts" and "An act page" with the stubbed-PostHog browser test, and that neither event carries anything about the visitor.
- [ ] 2.2 Add the show's name (`data-title-and-artists`) to `show_saved`, `show_unsaved`, `ticket_link_opened` and `show_added_to_calendar`; verify the modified "A show saved" and "A ticket link" scenarios and the calendar event's properties.

## 3. The dashboard

- [ ] 3.1 Write `core/analytics_dashboard.py`: the dashboard and the sixteen charts of design Decision 1, built with small query helpers; verify "Charts use sent events" (keys unique, names and descriptions present, every event one the site sends).
- [ ] 3.2 Write `sync_posthog_dashboard` (create, update, delete its own charts by key, delete the wizard's dashboard, `--dry-run`); verify "First run", "A chart changed", "A chart removed", "Dry run", "The wizard's dashboard", "No key" and "A failed request" against a mocked PostHog, and that the key appears only in the `Authorization` header.

## 4. Finish

- [ ] 4.1 Run the whole suite with the network blocked and verify it passes, with every scenario in this change's specs covered by a test.
- [ ] 4.2 After the events are deployed, run `sync_posthog_dashboard --dry-run`, then for real; verify the dashboard in PostHog shows all sixteen charts, that the wizard's dashboard is gone, and that a second run changes nothing.
- [ ] 4.3 Update `PRODUCTION.md` (the dashboard, how to change a chart and rerun the command, the personal key's scopes and where it's kept, the two new events) and `AGENTS.md`'s Secrets (`POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, `POSTHOG_APP_HOST`); verify both describe the shipped behavior.

## Workflow follow-up

- Rebase on `main` once PR #86 is merged.
- Archive with `/opsx:archive add-analytics-dashboard` once every task is ticked and every scenario has a passing test.
