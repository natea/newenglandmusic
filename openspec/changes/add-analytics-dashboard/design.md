# Design

## Context

- PostHog (US cloud, project 735651) receives, from the browser only: `$pageview`, `$pageleave`, autocaptured clicks, and the named events in `core/static/core/js/analytics.js` (`search`, `search_suggestion_chosen`, `show_saved`/`show_unsaved`, `preview_played`, `ticket_link_opened`, `show_added_to_calendar`, `calendar_feed_subscribed`, `deck_act_passed`, `deck_shows_saved`). IPs are discarded after GeoIP, so events carry `$geoip_country_name`, `$geoip_subdivision_1_name` (state) and `$geoip_city_name`, plus PostHog's `$referring_domain`, `$device_type` and `$pathname`.
- PostHog's API: saved insights at `/api/projects/:project_id/insights/` (create, update, delete), authenticated by a personal API key as a bearer token with `insight:read` / `insight:write` (PostHog's product analytics API docs). Dashboards are managed the same way at `/api/projects/:project_id/dashboards/` (`dashboard:write`); the exact insight body (an `InsightVizNode` wrapping a `TrendsQuery` or `FunnelsQuery`) is copied from an insight built in PostHog's UI and read back with `GET` (task 1.2) rather than written from memory.
- The wizard left a dashboard ("Analytics basics (wizard)", 2352999) of five charts over server-side events that are no longer sent.
- Each listed show's markup already carries its name (`data-title-and-artists` on the `event-<id>` element) and the search results view already counts each kind's matches; an act page knows its act, kind and next show.

## Goals / Non-Goals

**Goals:**
- Answer, at a glance: how many visitors, from where in New England; what they search for and whether they find it; which acts draw visits; whether visits become saves, plays and ticket clicks; whether the discovery deck is used.
- Charts changed by code review and one command, not by hand in PostHog.

**Non-Goals:**
- Alerts, subscriptions or scheduled reports (PostHog can add these later on the same dashboard).
- Charts of server-side work (event fetching, AI cost): not sent to PostHog.
- A public stats page.

## Decisions

### 1. The dashboard and its charts
"StageHopper: how the site is used", default range the last 30 days, in five rows. "Trend" is a line by day unless noted; every chart filters `$pathname` away from `/admin` only implicitly, since the admin doesn't load PostHog.

**Audience**
1. **Visitors and pageviews:** trend of unique visitors and of `$pageview`, by day. *Is the site growing?*
2. **Where visitors are:** `$pageview` unique visitors broken down by `$geoip_subdivision_1_name`, filtered to `$geoip_country_code = US`, as a bar chart. *Which New England states (and which others) we reach.*
3. **New England towns:** `$pageview` unique visitors broken down by `$geoip_city_name`, filtered to the six New England states, as a table of the top 25. *Which parts of New England: Boston, Worcester, the Pioneer Valley…*
4. **How they arrive:** `$pageview` broken down by `$referring_domain` (top 10, "$direct" included), as a table. *Search engines, Instagram, links from venues?*
5. **Phone or computer:** `$pageview` broken down by `$device_type`, as a pie. *How much of the site is used on phones.*

**Search**
6. **Searches:** trend of `search` and `search_suggestion_chosen`. *How much search is used, and how often a suggestion is picked instead of a full search.*
7. **Top searches:** `search_results_viewed` broken down by `query`, as a table of the top 25 with counts. *What people look for.*
8. **Searches that found nothing:** `search_results_viewed` where `total = 0`, broken down by `query`, as a table. *Acts and venues people want that the site lacks: the editors' to-do list.*
9. **Suggestions by kind:** `search_suggestion_chosen` broken down by `kind`, as a bar. *Do people look for bands, artists, venues or shows?*

**Acts**
10. **Most-viewed acts:** `act_page_viewed` broken down by `name`, as a table of the top 25. *Which acts draw visits.*
10a. **Act pages with and without a show:** `act_page_viewed` broken down by `has_upcoming_show`, as a pie. *Do people visit acts with nothing coming up?*
11. **From search to tickets:** a funnel `search_suggestion_chosen` (kind band or artist) → `act_page_viewed` → `ticket_link_opened`, within one day. *Does finding an act lead to buying a ticket?*

**Shows**
12. **Saves, plays and ticket clicks:** trend of `show_saved`, `preview_played` and `ticket_link_opened`. *The actions that mean someone plans to go.*
13. **Most-clicked shows:** `ticket_link_opened` broken down by `show`, as a table of the top 25. *Which shows people go on to buy.*
14. **Plays by service:** `preview_played` broken down by `service`, as a bar. *Which players people use (and whether Apple Music and YouTube are worth their upkeep).*
15. **Calendars:** `show_added_to_calendar` broken down by `how`, plus `calendar_feed_subscribed`, as a bar over the range. *Do people take shows into their calendars, and subscribe to feeds?*

**Discovery deck**
16. **The deck:** trend of `deck_act_passed` and of the sum of `deck_shows_saved.count`. *Is the deck used, and does it lead to saved shows?*

### 2. Two new events, from what each page already has
- `search_results_viewed` is captured by `analytics.js` on load from a `search-counts` JSON block (Django's `json_script`, safe for any search words) holding the query and the counts the view already has: `acts`, `venues`, `upcoming`, `past`, `pages`, `total`. A no-results page carries `total: 0`.
- `act_page_viewed` is captured on load from an `act-view` JSON block on the act page (`name`, `kind`, `has_upcoming_show`).
- Show events read the name from the show's `data-title-and-artists` beside its ID; the act page's and search results' show rows gain that attribute, as the listing's already have it. No event carries anything about the visitor.

### 3. Definitions as Python, synced by a command
`core/analytics_dashboard.py` holds `DASHBOARD` (name, description) and `CHARTS`, a list of `{key, name, description, query}` where `query` is the PostHog query JSON built by small helpers (`trend(events, breakdown=…)`, `funnel(steps, window=…)`, `table(...)`), so the seventeen definitions stay short and alike. `sync_posthog_dashboard` lists the project's dashboards and insights, finds its own by the key it stores in each insight's description footer ("chart key: <key>") and by the dashboard's name, then creates, updates or deletes so PostHog matches `CHARTS`; it deletes the wizard's dashboard by its name. Requests use `requests`, already a dependency.
*Alternatives:* build by hand (rejected by the decision to keep charts in code); Terraform's PostHog provider (rejected: a new tool for seventeen charts).

### 4. Credentials
`POSTHOG_PERSONAL_API_KEY` is created in PostHog (Settings → Personal API keys) scoped to project 735651 with `insight:read`, `insight:write`, `dashboard:read`, `dashboard:write`, kept in local `.env` only: the command is run by hand, never by the scheduled jobs, so the key isn't put on Render. `POSTHOG_PROJECT_ID=735651`, `POSTHOG_APP_HOST=https://us.posthog.com`.

### 5. Tests
Chart definitions are checked offline (keys unique, names and descriptions present, every event named one the site sends). The command runs against a fake PostHog (mocked HTTP, in-memory dashboards and insights) for each spec scenario, and asserts the key is only ever in the `Authorization` header. The new events use the browser test's stubbed `window.posthog`.

## Risks / Trade-offs

- **The query schema** is PostHog's and changes; copying it from a real insight (task 1.2) and testing shapes, not PostHog's exact JSON, keeps the risk to a failed sync with PostHog's error, which the command reports.
- **Counts are low by an unknown share** (ad blockers block PostHog); the charts show trends and rankings, which survive that, better than absolute numbers.
- **`query` on search events** occasionally holds something personal someone typed; the privacy page says searches are recorded, and the charts show only the top 25.
