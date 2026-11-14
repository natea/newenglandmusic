# Tasks

## 1. The PostHog project

- [ ] 1.1 Nate signs in to PostHog as `nate@stagehopper.app` and creates (or picks) the StageHopper project, noting its region (US or EU) and project API key; in the project's settings, turn on "Discard client IP data" and leave session replay off; verify both settings show in the project's settings page.

## 2. The wizard, reviewed

- [x] 2.1 Nate runs `npx -y @posthog/wizard@latest` in this change's worktree, signing in as `nate@stagehopper.app` and choosing the project from 1.1; verify `git status` lists the files the wizard changed and that `.env` (not committed) holds the key.
- [x] 2.2 Review the wizard's diff against design Decision 1: remove server-side setup (the `posthog` package from `requirements.txt`, any `AppConfig.ready()` init, `PosthogContextMiddleware`) and any key written into code; keep or add the browser snippet in `base.html`'s analytics block; verify `git diff` shows no key in a tracked file (`git grep -n "phc_"` finds nothing) and no server-side PostHog code.

## 3. PostHog on every page

- [x] 3.1 Read `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` (default `https://us.i.posthog.com`) in `nycnoise/settings/base.py`, pass them through `core/context_processors.py`, and render the snippet with design Decision 3's init options only when the key is set; confirm against the loaded SDK that `opt_out_capturing`, `opt_in_capturing` and `has_opted_out_capturing` exist; add both names to `.env.example` and `render.yaml` (`sync: false`); verify with Django tests for "Switched on", "Switched off", "Not in the admin" and "No session recording".
- [x] 3.2 Add `core/static/core/js/analytics.js` (`window.siteAnalytics.capture`, a no-op when PostHog is off or opted out, plus the delegated listener for `a.ticket`, `a.ical`, `a.gcal`, `a.calendarLink` with `transport: "sendBeacon", send_instantly: true`), and call it from `search-suggest.js` (`search`, `search_suggestion_chosen`), `saved_shows.js` (`show_saved`, `show_unsaved`), `artist_preview.js` (`preview_played`) and `discover.js` (`deck_act_passed`, `deck_shows_saved`); verify with a Playwright test against a stubbed `window.posthog` for "A search", "A suggestion chosen", "A show saved", "A play button" and "A ticket link", and that the deck and calendar events carry their properties.

## 4. Privacy

- [x] 4.1 Rewrite the privacy page's Analytics section (PostHog, its cookie, what it records and doesn't, the GoatCounter sentence kept) with the turn-off / turn-on control; verify "The privacy page describes it" with a Django test and "Turning it off" with the Playwright stub (no capture after opting out, and captures resume after opting back in).
- [x] 4.2 Check nothing identifying is sent: verify "A submission's email stays out" with the Playwright stub (submit an event with an email; no captured event or property holds it) and that no capture carries the location cookie's values or a distance.

## 5. GoatCounter

- [x] 5.1 Verify "GoatCounter switched on" with a Django test (`GOATCOUNTER_CODE="stagehopper"` renders `https://stagehopper.goatcounter.com/count` and GoatCounter's script, and nothing without the code).

## 6. Finish

- [x] 6.1 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/site-analytics/spec.md` covered by a test.
- [x] 6.2 Update `PRODUCTION.md` (the PostHog project, its two settings, IP discarding, the events and their properties, the opt-out, GoatCounter's code) and the Secrets section of `AGENTS.md` (`POSTHOG_PROJECT_TOKEN`, `POSTHOG_HOST`); verify both describe the shipped behavior.
- [ ] 6.3 With Nate's approval, set `POSTHOG_PROJECT_TOKEN`, `POSTHOG_HOST` and `GOATCOUNTER_CODE=stagehopper` on Render's web service, deploy, and verify on the live site that the page includes PostHog and GoatCounter, and that a pageview and a `search` event appear in PostHog's activity view and a visit in GoatCounter.

## Workflow follow-up

- Archive with `/opsx:archive add-posthog-analytics` once every task is ticked and every scenario has a passing test.
