## Why

Today a change built by the loop can be judged only by its pull request's diff, or by merging it, which puts it on the live site. Sooz, Mark and Nate need to see a change working before it merges, on data that looks like the live site's. On 9 November 2026 Nate asked for a copy of the production database, not demo data. On 12 November he chose a preview step before the merge (`building → preview-ready → awaiting-merge`).

Render offers two kinds of preview. Only one is safe here. A **pull request preview** copies the web service's settings, `DATABASE_URL` included. `bin/build.sh` runs `migrate` on every build. So the first preview of a pull request with a migration would change the live database, and anything saved on a preview would show up on the live site. A **preview environment** copies the whole blueprint, including a new, empty database, for each pull request. This change uses preview environments.

## What Changes

- **Each pull request gets its own preview of the site.** `render.yaml` turns on preview environments. For each pull request against `main`, Render builds the web service and a database of its own, and deploys them at their own `onrender.com` address. Render deletes the preview when the pull request is merged or closed, or after 7 days without a push.
- **The preview runs on a cleaned copy of today's live data.** After the preview's first deploy, a seed script:
  1. copies the live database through a read-only database role;
  2. leaves out the tables that hold only people's data: subscribers, sign-in codes, weekly-email choices, mail requests and sessions;
  3. applies the pull request's migrations on top;
  4. replaces the remaining personal fields: admin emails and passwords, and the submitter's email on events.

  Venues, acts, events and pages stay as they are.
- **A preview never reaches the outside world.** Settings in previews:
  - send no email;
  - carry no API keys for Spotify, Apple Music, YouTube, Google, Ticketmaster, Eventbrite, SeatGeek, Last.fm, Anthropic or PostHog;
  - count no analytics.

  The scheduled jobs (daily, weekly and the weekly email) are left out of previews. The play buttons already stored in event pages still play, since they need no key to show.
- **Changes that touch only specs or docs get no preview.** A build filter skips them, so an OpenSpec draft or a docs fix costs nothing.
- **A preview admin can sign in.** The seed creates one admin account, with a password set for previews only, so Nate can check admin changes.

Out of scope:
- **The issue side, in intentable.** That is posting the preview's address on the issue, moving it to `preview-ready`, and asking "looks right?". Render reports each preview's deploy to GitHub as a deployment, with its address. The bridge can read that, as `add-delivery-board` reads production's deploys. It will be its own change in intentable, once this one is live.
- **Previews from Fabro's sandboxes,** which the plan first proposed. Their links stop working when the sandbox stops, by default after two idle hours.
- **Keeping a preview after its pull request closes unmerged.** Render deletes it then. To keep a change viewable, its pull request stays open; the board shows it in `awaiting-merge`.

## Open questions for G2

1. **Render's plan.** Preview environments need a **Pro workspace plan** or higher. Each preview's web service and database are billed by the second on top of that. Is the workspace on Pro, or worth moving to it?
2. **How long an idle preview lives.** 7 days without a push is proposed. Longer keeps links working for slow reviews, at the cost of idle previews.
3. **Which pull requests get a preview.** Automatic (every pull request that touches code) is proposed, so the loop needs no change to its pull request titles. The alternative is manual: only pull requests with `[render preview]` in the title.
4. **Getting the read-only credentials to the preview.** The seed needs a read-only connection to the live database. Variables set only in the dashboard (`sync: false`) aren't copied to previews, and `previewValue` lives in the repository, so it can't hold a secret. The design proposes a dashboard-only environment group that Render copies into previews. Whether Render copies a group's dashboard values is the first thing to check. If it doesn't, the fallback is a nightly cleaned dump in a private bucket, which previews fetch.

## Capabilities

### New Capabilities

- `preview-environments`: a preview of the site for each pull request, on its own database seeded from a cleaned copy of the live data, cut off from email, outside APIs, analytics and the scheduled jobs.

### Modified Capabilities

None. The scheduled jobs' requirements are unchanged for production. Leaving them out of previews is stated in `preview-environments`.

## Impact

- **Code:**
  - `render.yaml`: `previews` on the blueprint, each service's preview settings, preview plans, build filters, preview values and the seed hook;
  - a new `bin/preview-seed.sh`;
  - a new management command, `scrub_preview_data`;
  - `PRODUCTION.md`: setting up previews, the read-only role and what previews cost.
- **Render:** the Pro workspace plan; a read-only Postgres role on the live database; one web service and one database per open pull request while it lives.
- **Data:** the live database is read, never written, by the seed. Personal data never reaches a preview: personal tables aren't copied, and the scrub replaces the rest before the preview is reachable by anyone else.
- **Depends on:** nothing in the fork. The loop's use of previews (`preview-ready`) waits for a follow-up change in intentable.
