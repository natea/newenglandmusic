## Why

PostHog now receives the site's pageviews and key actions, but its only dashboard is the one the wizard built for server-side events that never arrive, so it stays empty. The editors need a dashboard that answers their questions at a glance: how many people use the site and from where, what they search for and whether they find it, which acts draw visits, and whether visits turn into saved shows, plays and ticket clicks. Two of those questions need data the site doesn't send yet.

## What Changes

- **A "StageHopper: how the site is used" dashboard** in PostHog project 735651, of about fifteen charts grouped as Audience, Search, Acts, Shows and the Discovery deck (listed in design.md), each built on events the site sends.
- **Defined in the repo, created by a command:** the charts are written down in `core/analytics_dashboard.py`, and `sync_posthog_dashboard` creates or updates the dashboard and its charts through PostHog's API, so a change to a chart is a reviewed change rerun with one command. It's run by hand, with a personal API key kept in `.env`, not on Render.
- **Two new events:** `search_results_viewed` on the results page (the words searched and how many bands and artists, venues, upcoming and past shows, and pages matched, so searches that find nothing are visible), and `act_page_viewed` on a band's or artist's page (the act, its kind, and whether it has an upcoming show).
- **A readable show name** on the show events (`show_saved`, `show_unsaved`, `ticket_link_opened`, `show_added_to_calendar`): the show's title and artists as the listing prints them, beside its ID, so "top shows" tables read as names.
- **The wizard's empty dashboard** ("Analytics basics (wizard)") is deleted by the command's first run, with its notebook kept.

## Capabilities

### New Capabilities
- `analytics-dashboard`: the dashboard of how the site is used, defined in the repo and kept in step with PostHog by a command.

### Modified Capabilities
- `site-analytics`: two new events (`search_results_viewed`, `act_page_viewed`), and a `show` name on the show events.

## Impact

- **Depends on** PR #86 (the archived `add-posthog-analytics` and its `site-analytics` spec), from whose branch this one starts.
- **Code:** `core/analytics_dashboard.py` (the charts), `core/management/commands/sync_posthog_dashboard.py`; `core/static/core/js/analytics.js` and the search results and act page templates (the new events, from data the page already has); the show events' properties.
- **Configuration:** `POSTHOG_PERSONAL_API_KEY` (a personal API key with `insight:write` and `dashboard:write` only, local `.env` only, never on Render or in a log), `POSTHOG_PROJECT_ID` (735651) and `POSTHOG_APP_HOST` (`https://us.posthog.com`, the app's address, not the event host).
- **No new dependency, no model change.**
- **Tests:** never call PostHog: the command's API calls are mocked, the chart definitions are checked for shape, and the new events are checked with the stubbed `window.posthog`.
