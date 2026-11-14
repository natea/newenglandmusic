# Design

## Context

- `core/templates/core/base.html` already holds two switched-off analytics hooks, GoatCounter (`GOATCOUNTER_CODE`) and Google Analytics (`GOOGLE_ANALYTICS_ID`), passed to every page by `core/context_processors.py` and tested in `core/tests/test_site_settings.py`. Neither is set on Render. The admin uses Django's own templates, not `core/base.html`.
- The site has no accounts, no build step for its JavaScript (plain scripts in `core/static/core/js/`, vendored libraries under `core/static/core/vendor/`), and its stored event HTML (`Event.baked_html_template`) holds the "tix" link (`a.ticket`), while the icon row (`a.ical`, `a.gcal`) and the calendar feed links (`a.calendarLink`) are rendered per request.
- The key actions already live in scripts: search and suggestions in `search-suggest.js` (`onConfirm`, Enter with nothing chosen), saving in `saved_shows.js`, play buttons in `artist_preview.js` (one delegated click handler), the deck in `discover.js` (Skip, and the picker's Save).
- Tests never touch the network (`PYTHONPATH=…/netblock` in CI; browser tests abort every request that isn't to the test server, `core/tests/browser.py`).

## Goals / Non-Goals

**Goals:**
- One place that knows how to send an event, so the named events read the same everywhere and do nothing when PostHog is off or opted out.
- Keep the wizard's speed without taking on code the project doesn't need.

**Non-Goals:**
- Server-side events, identifying visitors, feature flags, experiments, surveys, session replay, heatmaps beyond PostHog's defaults.
- A reverse proxy to get past ad blockers (some visitors won't be counted; see Risks).
- Removing or changing the Google Analytics hook.

## Decisions

### 1. The wizard runs first, on this change's branch, and its output is reviewed, not taken whole
Nate runs `npx -y @posthog/wizard@latest` in this change's worktree, signs in as `nate@stagehopper.app` and chooses the project and region. The wizard detects Django and edits files. PostHog's docs say it installs "the relevant PostHog SDKs", client- and server-side, and writes the project's credentials to `.env`; PostHog's Django guide is server-side only (the `posthog` package, `posthog.api_key` / `posthog.host` set in an `AppConfig.ready()`, and `PosthogContextMiddleware`) and adds no browser snippet. So the diff is reviewed against this design: drop the server-side setup (the package, the `ready()` init, the middleware), keep or add the browser snippet in the existing analytics block of `base.html` beside GoatCounter, and read its key and host from `POSTHOG_PROJECT_KEY` / `POSTHOG_HOST` in `settings/base.py` rather than any key written into code. `.env` is never committed; `.env.example` gets the two names with empty values.
*Alternative:* hand-write the snippet without the wizard. Rejected only because Nate wants the wizard's guided project setup; the result is the same few lines.

### 2. Browser-only, with PostHog's standard loader
PostHog loads from its own host through its standard snippet (the loader stub fetches `array.js` from the region's assets host). No server-side SDK: there are no accounts and nothing the server knows that the page doesn't.
*Alternatives:* vendor `posthog-js` into `core/static/core/vendor/` (rejected: large, released often, and PostHog's loader already pins compatible code); an npm build step (rejected: the project has none).

### 3. Initialised for privacy
`posthog.init(key, {api_host: POSTHOG_HOST, defaults: "2026-08-30", person_profiles: "identified_only", disable_session_recording: true, autocapture: true})`, spelling out the privacy options even where they're PostHog's defaults (`identified_only` is; session recording isn't off by default) so a later default change can't widen what's collected. `identify` is never called, so every visitor stays anonymous and outside person profiles; PostHog's default persistence (`localStorage+cookie`) keeps its first-party cookie. Autocapture records clicks, not what's typed into inputs. In the PostHog project's settings, "Discard client IP data" is turned on and session replay left off (tasks 1.x), since a visitor's IP is personal data the site has no use for.

### 4. One small events script that every other script calls
`core/static/core/js/analytics.js` (loaded right after the snippet, only when PostHog is on) defines `window.siteAnalytics.capture(name, properties)`, which calls `posthog.capture` only when PostHog is loaded and the visitor hasn't opted out, and is a no-op otherwise. A tiny inline fallback defines a no-op `siteAnalytics` when PostHog is off, so the other scripts never check. The scripts that own each action call it: `search-suggest.js` (`search_suggestion_chosen` in `onConfirm`; `search` when the form submits), `saved_shows.js` (`show_saved` / `show_unsaved`), `artist_preview.js` (`preview_played`), `discover.js` (`deck_act_passed`, `deck_shows_saved`). Links the server renders (`a.ticket`, `a.ical`, `a.gcal`, `a.calendarLink`) are caught by one delegated click listener in `analytics.js`, so the stored event HTML needn't be re-rendered. The full search is captured on the form's submit, before the page navigates, with `capture(name, props, {transport: "sendBeacon", send_instantly: true})`, PostHog's documented way to send an event right before navigation; the same options cover the ticket, calendar and feed links, which leave the page.
*Alternative:* rely on autocapture alone. Rejected: autocapture events are anonymous clicks; named events with properties ("kind: band", "service: youtube") are what answer the product questions.

### 5. The opt-out lives on the privacy page and uses PostHog's own switch
The privacy page's Analytics section gets a button ("Turn off analytics for this browser" / "Turn analytics back on") that calls PostHog's opt-out and opt-in methods (`opt_in_capturing` is in the config reference; the opt-out and status methods, `opt_out_capturing` and `has_opted_out_capturing`, are confirmed against the loaded SDK before building, task 3.1); PostHog remembers the choice in the browser (`opt_out_capturing_persistence_type`) and sends nothing after opting out. Without JavaScript PostHog never loads, so no control is needed then. The section's text names PostHog, its cookie, and what it doesn't record, and keeps the existing GoatCounter sentence.

### 6. GoatCounter is a setting, not code
Its hook already renders `https://<code>.goatcounter.com/count` with GoatCounter's script; setting `GOATCOUNTER_CODE=stagehopper` on Render (with approval) switches it on. GoatCounter sets no cookie and needs nothing on the privacy page beyond the sentence it already has.

### 7. Tests stay offline
Django tests check the snippet and `analytics.js` render only when `POSTHOG_PROJECT_KEY` is set (with the configured host), never in the admin, and that GoatCounter renders for its code. A Playwright test serves pages with PostHog switched on but its host blocked, injects a stub `window.posthog` before the page's scripts run (`add_init_script`), drives each key action, and asserts the captured names and properties; it also checks the opt-out sends nothing afterwards and that no capture carries an email or a location. The stub, not PostHog, is what's tested against, so nothing leaves the test server.

## Risks / Trade-offs

- **Ad blockers** block PostHog's hosts, so counts are low by an unknown share. A first-party proxy would fix it but is out of scope.
- **The wizard's output can change** between releases; the review in Decision 1 is the guard, and the tests check the behavior, not the wizard's exact lines.
- **A third-party script on every page,** loaded from PostHog's host: if PostHog is slow or down, the site still works (the loader is async and the events are no-ops until it's ready).
- **The cookie** recognises a returning browser across visits; the privacy page says so and offers the opt-out. A consent banner was considered and declined: the site has no accounts or advertising, records nothing identifying, and serves a US audience.
- **Search words are sent.** They can, rarely, hold something personal someone typed; they're what search analytics needs, and the privacy page says searches are recorded.
