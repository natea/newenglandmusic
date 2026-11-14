## Why

The site records nothing about how it's used: its Google Analytics and GoatCounter hooks are both switched off in production. With search, the A–Z of acts, saved shows, play buttons and the discovery deck now live, we need to know what visitors actually do (what they search for, whether they find it, what they save and play, whether they go on to tickets) to decide what to build next.

## What Changes

- **PostHog on every public page,** from the PostHog account `nate@stagehopper.app`, set up with PostHog's wizard (`npx -y @posthog/wizard@latest`), which Nate runs; the wizard's changes are then reviewed against this design and kept only where they fit it.
- **Pageviews and autocaptured clicks,** plus **named events for the site's key actions:** a search run, a suggestion chosen (with its kind), a show saved or unsaved, a play button pressed (with its service), a ticket link followed, a show added to a calendar, a calendar feed subscribed to, and a card saved or passed in the discovery deck.
- **A first-party PostHog cookie,** so returning visitors are recognised; no accounts, no names or email addresses sent, no session replay, no person profiles for anonymous visitors.
- **The privacy page says so:** what PostHog records, that it sets a cookie, and a way to opt out (a link on the privacy page that turns PostHog off in that browser).
- **Switched by settings:** PostHog loads only when `POSTHOG_PROJECT_TOKEN` is set (with `POSTHOG_HOST` for the account's region), so development, tests and the admin never send anything.
- **GoatCounter switched on too,** as Nate asked: its existing hook needs only `GOATCOUNTER_CODE=stagehopper` on Render. The Google Analytics hook stays as it is, unused.

## Capabilities

### New Capabilities
- `site-analytics`: what the site measures about its own use (PostHog and GoatCounter), what it never sends, how it's switched on, and how the privacy page describes it.

### Modified Capabilities
None. The privacy page's existing requirement (in `youtube-artist-preview`) is unchanged; what it must say about analytics is a `site-analytics` requirement.

## Impact

- **Code:** `core/templates/core/base.html` (the PostHog snippet, beside the GoatCounter and Google Analytics hooks), `core/context_processors.py` and `nycnoise/settings/base.py` (the two settings), a small `core/static/core/js/analytics.js` for the named events, and the scripts whose actions it names (`search-suggest.js`, `saved_shows.js`, `artist_preview.js`, `discover.js`); `core/templates/core/privacy.html`.
- **Dependency:** PostHog's JavaScript, loaded from PostHog's own host by its standard snippet; the wizard may also add `posthog` (Python) to `requirements.txt`, kept only if the design uses it (it doesn't: there are no accounts and nothing to send from the server).
- **Configuration:** `POSTHOG_PROJECT_TOKEN` and `POSTHOG_HOST` in `.env`, `.env.example`, `render.yaml` and on Render (the project key is PostHog's public, browser-side key); `GOATCOUNTER_CODE=stagehopper` on Render. Writing them to Render needs Nate's approval.
- **Accounts:** a PostHog project under `nate@stagehopper.app`; in its settings, IP address capture turned off and session replay left off.
- **Tests:** never touch PostHog: they check the snippet renders only when switched on, and a browser test checks the named events with PostHog's `capture` stubbed in the page.
