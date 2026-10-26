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

**For the scheduled jobs:** set these on the web service. The cron jobs copy them from it on each blueprint sync, so after changing one, run a blueprint sync (or redeploy the jobs) for them to see it.
- `ANTHROPIC_API_KEY`: AI event extraction and labelling events by kind.
- `TICKETMASTER_API_KEY`: the Consumer Key of a Ticketmaster app.
- `EVENTBRITE_API_KEY`: the private token of an Eventbrite account, from eventbrite.com/platform/api-keys.
- `GOOGLE_PLACES_API_KEY`: in Google Cloud, restrict it to the Places API (New) and cap its daily quota.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: the sheet sync's service-account key (see "Reading the sheet on a server").

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

**Migrations** run at the end of the build (Render's free plan has no pre-deploy command), so a failed migration fails the build and the new code isn't deployed. On a paid plan they can move to `preDeployCommand` in `render.yaml`.

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
- **Plans:** $7 a month for the web service; the database is still free.
  - **Web service:** `0.5c-512mb` ($7 a month), with two gunicorn workers.
    - It stays awake. The `free` plan slept after 15 minutes without visitors and took about a minute to wake.
    - It has a Shell tab for one-off commands, which can also run from your machine (see below).
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
2. Once the database exists, load the local data into it (see below). The first build has already migrated the empty database, and the restore replaces it with the local data, which has the same migrations.
3. The local admin account comes with the dump. For a separate production account, run `createsuperuser` against Render's database (see below).
4. Check the site at its `onrender.com` address, and log in to `/admin/`.

**Loading the local database.** Make a dump locally, then restore it into Render's database. The restore needs its **External Database URL**, from the database's page in the dashboard.

The jobs share `check_event_sources`' results through the database. If your local results are still only in an old `event_sources.csv`, import them first, so the server doesn't have to crawl every venue again:

```sh
venv/bin/python manage.py import_event_sources event_sources.csv --dry-run
venv/bin/python manage.py import_event_sources event_sources.csv
```

Then dump and restore:

```sh
# DATABASE_URL here is the local one, from .env
pg_dump --format=custom --no-owner --no-privileges --exclude-table-data=django_session \
  "$DATABASE_URL" > newenglandmusic.dump
pg_restore --no-owner --no-privileges --clean --if-exists \
  --dbname "<External Database URL>" newenglandmusic.dump
```

Keep the dump out of the repo, since it holds admin password hashes.

The dump includes admin accounts, with their password hashes, and the stored HTML of every event, so the events need no re-render. If it's older than the code, run `resave_all_events` against Render's database after deploying.

**One-off commands.** Run them in the web service's Shell tab, or from your machine with `DATABASE_URL` set to Render's **External Database URL**:

```sh
DATABASE_URL="<External Database URL>" DJANGO_SETTINGS_MODULE=nycnoise.settings.prod \
  venv/bin/python manage.py createsuperuser
```

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
| `lookup_venue_places --refresh-stale` | daily, after the lookup | Places: refreshes coordinates more than 25 days old by place ID, so each venue about every 25 days: roughly 880 Place Details Pro calls a month, inside the 5,000 free. Every run also deletes coordinates older than 30 days, as Google's terms require |
| `check_event_sources` | weekly | free, but it crawls every venue's site, so don't run it more often |
| `match_ticketmaster_venues` | weekly, after the source check | free (Ticketmaster allows 5,000 requests a day) |
| `match_eventbrite_organizers` | weekly, after the source check | free (Eventbrite allows 2,000 requests an hour). It fetches the pages of venues that link Eventbrite, politely, and links only new venues unless given `--recheck` |
| `fetch_events --all` | daily | Anthropic: about $0.30 per full run, so about $9 a month. Labelling new events adds a little more. Ticketmaster and Eventbrite: a few hundred requests each |

### How they run on Render

`render.yaml` defines two cron jobs, each running a script:

| Job | Schedule (UTC) | Script | Runs |
|---|---|---|---|
| `newenglandmusic-daily` | `0 10 * * *`: 5 or 6 am eastern | `bin/daily.sh` | sheet sync, Places lookup, coordinate refresh, `fetch_events --all` |
| `newenglandmusic-weekly` | `0 7 * * 0`: Sundays, before that day's daily run | `bin/weekly.sh` | source check, Ticketmaster and Eventbrite matching |

- **A failed step doesn't stop the job.** None of the steps needs the one before it to have succeeded: a failed sheet sync leaves the venues as they were, and they can still be fetched. The script runs every step, then exits with an error naming the failed ones, so Render marks the run failed and emails the workspace.
- **Builds:** the jobs build with `bin/build-job.sh`, which only installs the requirements. Only the web service migrates. Like the web service, they deploy a commit only once CI passes.
- **Setting them up:** after `render.yaml` changes on `main`, run a blueprint sync in the Render dashboard (the blueprint's page, **Manual Sync**). It shows the services it will create and their cost for approval.
- **Running one now:** trigger a run from the job's page in the dashboard, or with `render jobs create <service id> --start-command ./bin/daily.sh`. A manual run cancels one that's already running.
- **Cost:** each job is billed by the second of running time on `0.5c-512mb`, with a $1 minimum a month, so about $2 a month for both, plus the Anthropic usage above.

**Reviewing runs.** Each run of these commands is recorded in the database, wherever it runs, and listed newest first in the admin at `/admin/core/jobrun/`:
- **What a run shows:** its arguments, start time and duration, its outcome, a short summary of counts, the report it printed, and the error if it failed.
- **Outcome:** succeeded, failed, running, or "didn't finish", for a run still marked running six hours after it started (for example, one the host killed).
- **Pruning:** runs older than 90 days are deleted automatically.

**Logs.** The commands still print to the console as well, and the host keeps that output for a while: on Render, in each cron job's Logs tab. Scrapy's own logging appears only there, not in the recorded runs. The `logs/` files are a local convenience.

**Crawling.** The crawler identifies itself as `venue-db-event-check/1.0` and obeys robots.txt. It also skips Tixr, which blocks the crawling IP address. Keep the full crawl weekly. A data-centre IP gets blocked faster than a home one.

## Google Places terms

Google's terms allow storing a place ID indefinitely and its coordinates for up to 30 days, and nothing else from Places. `lookup_venue_places` keeps to that:
- **What's stored:** only each venue's place ID, coordinates, match status and when the coordinates were fetched. The name, address and open or closed status are used while a lookup runs, then discarded.
- **Refreshing:** the daily `--refresh-stale` run re-fetches coordinates by place ID before they're 30 days old.
- **Expiry:** every run deletes coordinates older than 30 days, even if its requests fail. The venue then uses its sheet coordinates until a refresh succeeds.

## Reading the sheet on a server

Locally, `sync_venues_from_gsheets` reads the sheet with the `gog` CLI, which signs in to Google as you through a browser. A server can't do that, so there it reads the sheet with a **Google Cloud service account** instead. The account can only read, and only sheets shared with it, so the sheet stays private. Set it up once:

1. **Create the account.** In the Google Cloud console, pick or create a project and enable the **Google Sheets API** for it. Under **IAM & Admin > Service Accounts**, create a service account; it needs no roles.
2. **Create its key.** On the account's **Keys** tab, add a key of type **JSON**. A file downloads; keep it out of the repo.
3. **Share the sheet.** Share the venue sheet copy ("Northeastern US Music Venues - v3 (venue-db copy)") with the account's email address, which ends in `iam.gserviceaccount.com`, as a **Viewer**. Don't share the original sheet.
4. **Give Render the key.** In the web service's **Environment** settings, set `GOOGLE_SERVICE_ACCOUNT_JSON` to the whole contents of the JSON file, then delete the downloaded file.
5. **Check it.** In the service's **Shell** tab, run `python manage.py sync_venues_from_gsheets --dry-run`. It should report the venues and areas with no errors. An error names the tab and what to fix, such as sharing the sheet with the account's email.

If the key ever leaks, delete it on the account's **Keys** tab and create a new one.

**Still to do:** a Render Cron Job that runs the sync and the other daily jobs every day.

## Launch checklist

- [ ] Postgres created, and `DATABASE_URL` set
- [ ] the required variables set, with `DJANGO_SETTINGS_MODULE=nycnoise.settings.prod` and a fresh secret key
- [ ] CI passes on `main`, and the Render build (static files) and pre-deploy (migrations) succeed
- [ ] the local database restored into Render's, and the site checked at its `onrender.com` address
- [ ] an admin user created: `python manage.py createsuperuser`
- [ ] the domain pointed at the host, and HTTPS working
- [ ] `ALLOWED_HOSTS` and `SITE_URL` match the domain
- [ ] the API keys restricted: Places to its API, Protomaps to the domain
- [ ] the scheduled jobs added (the sheet's service account set up first)
- [ ] Eventbrite's API terms checked for attribution and caching rules, since events imported from it are shown on the site
- [ ] the first `fetch_events` run checked in `/admin/core/alleventproxy/` before events are approved
- [ ] **before announcing or sharing the site:** Google Places terms met. Until then, keep the site unshared. As of 2026-10-25 it was deployed but kept private for this reason.
  - **Stored content:** done. Only place IDs and coordinates are stored, and coordinates are refreshed or deleted within 30 days (see Google Places terms above). The daily `--refresh-stale` job has to be running for pins to stay exact.
  - **Maps (still open):** "Places API results displayed on a map must be shown on a Google Map". The day maps use Protomaps. The options: switch the day maps to the Google Maps JavaScript API, which has its own cost; pin venues from a geocoder whose results may be stored (US Census or OpenStreetMap) and use Places only for matching and the MAP link; or get a reading of the terms that allows the current maps. Each is a separate change.
