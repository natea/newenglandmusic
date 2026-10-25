# Deploying New England Music

How to run this site in production. For running it locally, see `AGENTS.md`.

A deployment has three parts:

1. **A web process:** Django served by gunicorn, with static files served by WhiteNoise.
2. **A Postgres database.**
3. **Scheduled jobs** that refresh venues and fetch events, by running management commands on a timer.

> **Status:** the web process works as it is. The scheduled jobs are not ready to run on a server yet; see [Before the jobs can run on a server](#before-the-jobs-can-run-on-a-server).

## Configuration

Everything is configured through environment variables. `.env.example` lists them all with notes. On a host, set them in its dashboard rather than uploading a `.env` file.

**Required:**

| Variable | Production value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `nycnoise.settings.prod` (turns `DEBUG` off) |
| `DJANGO_SECRET_KEY` | a long random key; see below |
| `DATABASE_URL` | the Postgres connection string from your host |
| `ALLOWED_HOSTS` | your domain(s), comma-separated, e.g. `newenglandmusic.example,www.newenglandmusic.example` |
| `SITE_URL` | `https://` plus your domain, used in share links |
| `PROD_INTERNAL_API_SERVER`, `RC_DEVELOPER_INTERNAL_TOKEN` | inherited from nyc noise and not used by this fork; blank is fine, but they must be set |
| `DEBUG_TOOLBAR_ENABLE`, `PYINSTRUMENT_ENABLE`, `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION` | `false` unless you want them |

**The secret key.** Locally a UUID is fine. In production, use Django's own generator, which makes a longer and more random key:

```sh
venv/bin/python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Keep it only in the host's settings, never in git. Changing it logs everyone out of the admin. Some hosts can generate it for you (Render: `generateValue: true`).

**For the scheduled jobs:**
- `ANTHROPIC_API_KEY`: AI event extraction and labelling events by kind.
- `TICKETMASTER_API_KEY`: the Consumer Key of a Ticketmaster app.
- `GOOGLE_PLACES_API_KEY`: in Google Cloud, restrict it to the Places API (New) and cap its daily quota.

**Optional:**
- **`CONTACT_EMAIL`:** shown on the submit-event form.
- **`DEFAULT_FROM_EMAIL`:** the sender of outgoing email.
  - Submission emails go out through Amazon SES, so this must be an address verified in SES.
  - They also need `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
- **`PROTOMAPS_API_KEY`:** the home page's maps. In your Protomaps account, restrict it to your domain. `MAP_CENTER_LATITUDE`, `MAP_CENTER_LONGITUDE` and `MAP_ZOOM` set where the maps start.
- **`GOOGLE_ANALYTICS_ID`, `GOATCOUNTER_CODE`:** analytics. Each one loads only when it is set.

## The web process

**Tests:** GitHub Actions (`.github/workflows/django.yml`) runs the suite on every push to `main`. The build doesn't run them, because on the host they'd have to create a test database on the production Postgres server.

**Build** (`bin/build.sh`):
- installs `requirements.txt`
- compiles the SCSS and collects the static files

**Migrations** run after the build and before the new code goes live: on Render, as the pre-deploy command, so a failed migration stops the deploy.

**Start:**

```sh
gunicorn nycnoise.wsgi:application
```

`bin/serve.sh` adds an access-log format and binds port 8000.

**Python version:** 3.11, the same as local development. `render.yaml` pins it with `PYTHON_VERSION`, and CI uses the same version.

**Other hosting files from nyc noise:** check these before relying on them.
- **`Dockerfile`:** builds on Python 3.12.1.
- **`disco.json`:** a [Disco](https://disco.cloud) config, which runs `migrate` before each deploy.

## Deploying to Render

`render.yaml` is a Render Blueprint for the web service and its Postgres database, in the Virginia region. It doesn't include the scheduled jobs yet; see [Before the jobs can run on a server](#before-the-jobs-can-run-on-a-server).

- **What deploys:** Render deploys `main` from the GitHub repo [natea/newenglandmusic](https://github.com/natea/newenglandmusic), and only once CI has passed on that commit (`autoDeployTrigger: checksPass`). `origin` is the upstream nyc noise repo; never deploy from or push to it.
- **Plans:** $7 a month in total while the site is unshared.
  - **Web service:** `0.5c-512mb` ($7 a month), with two gunicorn workers.
  - **Database:** `free`, with these limits:
    - It expires 30 days after it's created, and Render deletes it 14 days after that.
    - It has no backups and holds 1 GB (the data is about 20 MB).
    - Only one free database is allowed per workspace.
  - **Keeping the data:** before the 30 days are up, either upgrade the database to a paid plan in the dashboard (it keeps its data, and `0.1c-256mb` is $10.50 a month), or dump it and restore into a new one. Until then, take your own dumps: `pg_dump --format=custom "<External Database URL>" > prod-YYYY-MM-DD.dump`.
- **Settings Render fills in:**
  - `DJANGO_SECRET_KEY` is generated.
  - `DATABASE_URL` comes from the database.
  - The service's `onrender.com` hostname is added to `ALLOWED_HOSTS` automatically.
  - Its URL is used as `SITE_URL` when that's blank.
- **Settings you're asked for when creating the Blueprint:** `ALLOWED_HOSTS` and `SITE_URL` (leave both blank until there's a custom domain), `PROTOMAPS_API_KEY`, `CONTACT_EMAIL` and `GOATCOUNTER_CODE`. All are optional.

**First deploy:**
1. In the Render dashboard, choose **New > Blueprint**, connect the GitHub repo and apply `render.yaml`.
2. Once the database exists, load the local data into it (see below), then trigger a deploy so the migrations run against it.
3. Create an admin user from the service's **Shell** tab: `python manage.py createsuperuser`.
4. Check the site at its `onrender.com` address, and log in to `/admin/`.

**Loading the local database.** Make a dump locally, then restore it into Render's database. The restore needs its **External Database URL**, from the database's page in the dashboard.

```sh
# DATABASE_URL here is the local one, from .env
pg_dump --format=custom --no-owner --no-privileges --exclude-table-data=django_session \
  "$DATABASE_URL" > newenglandmusic.dump
pg_restore --no-owner --no-privileges --clean --if-exists \
  --dbname "<External Database URL>" newenglandmusic.dump
```

Keep the dump out of the repo, since it holds admin password hashes.

The dump includes admin accounts, with their password hashes, and the stored HTML of every event, so the events need no re-render. If it's older than the code, run `python manage.py resave_all_events` from the Shell tab after deploying.

**A custom domain:** add it under the service's **Settings > Custom Domains**, then set `ALLOWED_HOSTS` to the domain and `SITE_URL` to `https://` plus the domain.

## Scheduled jobs

### Why not Celery?

Celery is the wrong tool here.
- **What it's for:** a task queue for work that a web request hands off. Sending an email after a form submission is the typical example.
- **What it would cost:** running it means a message broker (Redis or RabbitMQ), a worker process and a `celery beat` scheduler. That's three more things to deploy and monitor.
- **What we need:** a few long batch commands, run on a schedule, with nobody waiting on them.

**Use the host's scheduler to run management commands.** The command starts, does its work and exits, which is how these commands already behave. Choose by host:

| Host | Scheduler |
|---|---|
| Render | a **Cron Job** service: the same repo and environment variables, plus a `schedule` and a command |
| Fly.io, Railway, Disco | their scheduled-machine or cron feature |
| A plain server (VPS) | a **systemd timer**, or plain `cron`. Timers keep logs in the journal and don't start a run while the last one is still going |

**If we later need in-app background work:** for example, fetching one venue's events from a button in the admin. At that point, add a small database-backed queue such as **django-q2** or **django-tasks**. Both keep their tasks in the Postgres we already have, so no broker is needed. Even then, Celery isn't required.

### What to run, and how often

These run in this order. Each one depends on the one before it:

| Command | Suggested schedule | Cost per run |
|---|---|---|
| `sync_venues_from_gsheets` | daily | free |
| `lookup_venue_places` | daily (it only looks up venues without a match yet, so most days it does nothing) | Places: about one call per new venue. 5,000 calls a month are free |
| `check_event_sources --output <report path>` | weekly | free, but it crawls every venue's site, so don't run it more often |
| `match_ticketmaster_venues --report <report path>` | weekly, after the source check | free (Ticketmaster allows 5,000 requests a day) |
| `fetch_events --report <report path> --all` | daily | Anthropic: about $0.30 per full run, so about $9 a month. Labelling new events adds a little more. Ticketmaster: a few hundred requests |

**A single script would be simplest.** For example, `bin/refresh.sh` would run the daily commands in order and stop at the first failure, plus a weekly script for the crawl. Then the scheduler needs only two entries.

**Logs.** On a server, the commands should print to the console, and the host keeps it. The `logs/` files are a local convenience.

**Crawling.** The crawler identifies itself as `venue-db-event-check/1.0` and obeys robots.txt. It also skips Tixr, which blocks the crawling IP address. Keep the full crawl weekly. A data-centre IP gets blocked faster than a home one.

## Before the jobs can run on a server

These need fixing first. Each is a code change, so each needs its own OpenSpec proposal:

1. **The sheet sync uses the `gog` CLI.** gog signs in to Google as you, through a browser, so it can't sign in on a server. Two options:
   - Read the sheet with a **Google service account** instead, after sharing the sheet with the account's email address.
   - Use the sheet's **published CSV link**, which needs no credentials but makes the sheet public.
2. **The event-source report is a file.** `check_event_sources` writes `event_sources.csv`, and `match_ticketmaster_venues` and `fetch_events` read it. The file isn't in git, and most hosts give each run a fresh, empty disk. So the report has to live somewhere that persists:
   - in the database (a model holding each venue's best source; the best option)
   - on a mounted volume
   - in object storage
3. **Google Places terms.** The terms allow storing place IDs, but coordinates for only about 30 days. The venue-place-lookup design notes this. Before going public, either:
   - refresh coordinates monthly (`lookup_venue_places --refresh`, which costs Places calls), or
   - keep only the place IDs and look up coordinates when needed.

## Launch checklist

- [ ] Postgres created, and `DATABASE_URL` set
- [ ] the required variables set, with `DJANGO_SETTINGS_MODULE=nycnoise.settings.prod` and a fresh secret key
- [ ] CI passes on `main`, and the Render build (static files) and pre-deploy (migrations) succeed
- [ ] the local database restored into Render's, and the site checked at its `onrender.com` address
- [ ] an admin user created: `python manage.py createsuperuser`
- [ ] the domain pointed at the host, and HTTPS working
- [ ] `ALLOWED_HOSTS` and `SITE_URL` match the domain
- [ ] the API keys restricted: Places to its API, Protomaps to the domain
- [ ] the three blockers above fixed, then the scheduled jobs added
- [ ] the first `fetch_events` run checked in `/admin/core/alleventproxy/` before events are approved
- [ ] **before announcing or sharing the site:** Google Places terms met. Until then, keep the site unshared. As of 2026-10-25 it was deployed but kept private for this reason.
  - **Stored content:** Google allows storing only place IDs indefinitely, and coordinates for up to 30 days. The `refresh-place-coordinates` change removes the other stored Places fields and expires old coordinates.
  - **Maps:** "Places API results displayed on a map must be shown on a Google Map". The day maps use Protomaps, so either switch to Google Maps or pin venues from a geocoder whose results may be stored. Either one is a separate change.
