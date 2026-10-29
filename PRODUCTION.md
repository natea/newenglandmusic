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
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`: a Spotify app's credentials, for the listing's play buttons (see "Spotify play buttons"). The web service uses them too, because saving an event renders its buttons.
- `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_PRIVATE_KEY`, `APPLE_MUSIC_PREVIEWS`: a MusicKit key, and the switch that shows the Apple Music buttons (see "Apple Music play buttons").
- `LASTFM_API_KEY`: a Last.fm API account's key, for the artist matching's evidence (see "Last.fm evidence").
- `YOUTUBE_API_KEY`, `YOUTUBE_PREVIEWS`: a Google Cloud key restricted to YouTube Data API v3, and the switch that shows the YouTube buttons (see "YouTube play buttons").

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
| `match_spotify_artists --limit 500` | daily, after `fetch_events` | free, but rate limited. It searches Spotify for artist names it hasn't seen, and for automatic matches more than 30 days old, half a second apart, taking about 4 minutes. Spotify doesn't publish its limits, but the number of searches is what counts, not their pace: about 650 half a second apart (2026-10-27) and about 680 two seconds apart (2026-10-28) each got the app blocked for about a day. The block applies to the whole developer account, so a dev app's runs use up production's allowance too. 500 a morning stays under it, and clears a first run's backlog of about 2,700 names in about six days. When blocked, a run stops at once and keeps what it found, and the next morning's carries on. After the backlog, each morning searches only new names |
| `match_apple_music_artists --limit 1000` | daily, after the Spotify matching | free with the Developer Program membership. Like the Spotify matching, but also looks up each matched artist's top song. Requests go half a second apart, and a long rate-limit block stops the run the same way. It does nothing until the MusicKit key is set |
| `resolve_artists_with_lastfm --limit 300` | daily, after the Apple Music matching | free. For names several Spotify or Apple Music artists share, it reads Last.fm (half a second apart) and MusicBrainz (a second apart), taking up to about 8 minutes. It does nothing until `LASTFM_API_KEY` is set |
| `match_youtube_artists --limit 90` | daily, after the Last.fm resolving | free within YouTube Data API v3's 10,000 units a day. It matches only artists already matched on Spotify or Apple Music: first through Wikidata and MusicBrainz, then at most 90 searches for their Last.fm top track (101 units each). It does nothing until `YOUTUBE_API_KEY` is set |
| `fetch_events --all` | daily | Anthropic: about $0.30 per full run, so about $9 a month. Labelling new events adds a little more. Ticketmaster and Eventbrite: a few hundred requests each |

### How they run on Render

`render.yaml` defines two cron jobs, each running a script:

| Job | Schedule (UTC) | Script | Runs |
|---|---|---|---|
| `newenglandmusic-daily` | `0 10 * * *`: 5 or 6 am eastern | `bin/daily.sh` | sheet sync, Places lookup, coordinate refresh, `fetch_events --all`, Spotify and Apple Music matching |
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

## Spotify play buttons

The events listing shows a "▶ artist name" button for each artist matched to Spotify, in a row of its own below the event's text. Clicking it opens Spotify's embedded artist player below the buttons. Without JavaScript, the button is a link to the artist on Spotify.

**Setting up the Spotify app:**
1. At [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard), create an app. The account that owns it needs Spotify Premium: without it, Spotify's API stops answering, although buttons already matched keep working.
2. Tick only **Web API**. Spotify requires a redirect URI, and the play buttons don't use it; register the two that `add-spotify-followed-artists` will need: `https://newenglandmusic.onrender.com/spotify/callback` and `http://127.0.0.1:8001/spotify/callback`.
3. From the app's **Settings**, copy the Client ID and the client secret into `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`: locally in `.env`, and on Render on the web service, then run a blueprint sync so the cron jobs get them too.
4. Run `match_spotify_artists --dry-run --limit 50` to check the matches, then a full run.

**How matching works.** `match_spotify_artists` reads the artist names from each upcoming approved music event's title and artists text (`core/artist_names.py`).
- **Signing in:** it signs in to Spotify as the app (the Client Credentials flow), so no visitor signs in, and development mode's 5-user cap doesn't apply.
- **When a name is linked:** only when exactly one Spotify artist has the same name, ignoring case, accents, punctuation and a leading "The". Names shared by several artists are marked ambiguous, and names with no match are marked not found, so neither is searched again for 30 days.

**What's stored.** Spotify's terms forbid keeping a database of its content.
- **What's kept:** `SpotifyArtistLink` keeps only each name (normalized), its status, the Spotify artist ID, who set it, and when.
- **Re-checking:** automatic matches are searched again after 30 days.
- **Deleting:** a link is deleted once no upcoming event has named the artist for 30 days.

**Correcting a match.** At `/admin/core/spotifyartistlink/`:
- **Fixing or adding a match:** paste the artist's Spotify link (Share > Copy link to artist). This also works for a name the command hasn't seen, by adding a link.
- **Hiding a button:** tick **No Spotify artist**, or use the action of the same name.
- **Finding matches to review:** filter by source "Automatic". That's where a local band sharing its name with a different Spotify artist would show up.
- **Effects:** an editor's choice is never searched again or overwritten, and saving it re-renders that artist's upcoming events.

**Terms.** The player is Spotify's own widget, shown as Spotify makes it. Nothing loads from Spotify until a visitor clicks, so a page view sets no Spotify cookies. The Widget Terms bar using the player for commercial purposes, which this site doesn't do.

## Apple Music play buttons

Next to each Spotify button, an Apple Music button opens Apple's player for the artist's most popular song: the first of the Apple Music API's top songs, which Apple documents as ordered by popularity. Under the player, a "More by <artist> on Apple Music" link goes to the artist's page.
- **Why a song:** Apple's artist player exists, but plays nothing for visitors who aren't signed in to Apple Music, which is most visitors (tested 2026-10-27). The song player plays a 30-second preview for everyone, and full songs for subscribers who are signed in.
- **Without JavaScript,** the button is a link to the artist's page on Apple Music.
- **Signing in inside the player doesn't stick** (tested 2026-10-27 in Chrome and Safari, locally and on the live site, with and without the frame's sandbox). Apple's sign-in popup signs the visitor in, but the player in our page stays signed out: browsers keep a third-party frame's cookies apart, and Apple's player doesn't request storage access. Safari also opens Apple's popup at a size Apple sets, which can't be resized. So everyone gets the 30-second preview, and full songs through "View in Apple Music" or "More by … on Apple Music", which open Apple Music where the visitor is already signed in. A visitor can make it work for themselves by allowing third-party cookies for `[*.]apple.com` in their browser.

**Setting up the MusicKit key** (needs the Apple Developer Program membership):
1. At [developer.apple.com/account](https://developer.apple.com/account), under **Certificates, Identifiers & Profiles > Identifiers**, add a **Media ID**.
2. Under **Keys**, add a key with **Media Services (MusicKit, ShazamKit, Apple Music Feed)** enabled, configured with that Media ID. Download its `.p8` file: Apple allows this only once. Note the key's **Key ID**, and your **Team ID** from the **Membership** page.
3. Set `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY` (the `.p8` file's whole text) locally in `.env`, and on Render on the web service, then run a blueprint sync so the daily job gets them too. In `.env`, write the key's newlines as `\n` on one line. Then delete the downloaded file, or keep it somewhere safe outside the repo.
4. Run `match_apple_music_artists --dry-run --limit 30`, and check a few matches and their top songs.
5. Run it for real, and review the automatic matches at `/admin/core/applemusicartistlink/`.
6. Set `APPLE_MUSIC_PREVIEWS` to `true` on the web service and in `.env`, then run `resave_all_events` so the stored event pages get their buttons.

**What's stored:** for each name, only the Apple Music artist ID, its top song's ID and that song's album ID, with the same 30-day refresh and expiry as the Spotify links. An editor's artist is never changed, but its top song is refreshed. The site signs its own short-lived developer tokens from the key, on the server, so the key never reaches a browser. If the key leaks, revoke it under **Keys** and make a new one.

**Correcting a match** works as it does for Spotify: paste the artist's Apple Music page link, or tick **No Apple Music artist**. A pasted link looks up its top song at once.

**Still to settle before going public:** whether Apple's terms for promotional use of its content cover a concert listing.

## YouTube play buttons

Next to the Spotify and Apple Music buttons, a YouTube button opens YouTube's own player, from `youtube-nocookie.com`.
- **Who gets a button:** an artist gets one only when the match is certain. They must already be matched on Spotify or Apple Music, and one of these must tie them to the YouTube channel or video:
  - a Wikidata or MusicBrainz entry that links their Spotify or Apple ID to the channel;
  - the most-played track on their Last.fm page, on their own channel or their "<artist> - Topic" channel, with the same song (and, for a Topic video, the same album).

  The song never comes from Apple Music or Spotify. Apple's developer license (§3.3.6 D) allows MusicKit calls only "for purposes … facilitating access to Your end users' Apple Music subscriptions", and forbids using its "music-related text … separately from music playback". Spotify allows its metadata to be used only with its content. Song matches made before 2026-10-28 used Apple's top songs; a migration marked them (`song_source` "apple"), and the next run matches them again with the Last.fm track.
- **What it plays:**
  - the confirmed song's video;
  - or, for a channel found through Wikidata or MusicBrainz, the channel's uploads.
- **Without JavaScript,** the button is a link to the video or the channel on YouTube.

**Which Google Cloud APIs to enable:** only **YouTube Data API v3**. `match_youtube_artists` uses it to search for videos and to check channels and videos. It's free up to 10,000 quota units a day, and nothing is charged without billing turned on. Leave these off:
- **YouTube Embedded Player API:** the player is a plain iframe, which needs no API or key.
- **YouTube oEmbed API:** we don't fetch embed codes.
- **YouTube Analytics API and YouTube Reporting API:** these are for a channel owner's own statistics.

**Setting up the key:**
1. In the Google Cloud project, under **APIs & Services > Library**, enable **YouTube Data API v3**.
2. Under **Credentials**, create an API key. Under **API restrictions**, restrict it to YouTube Data API v3. It's used only from the server, so set **Application restrictions** to None, or to Render's outbound IP addresses. Don't choose **Websites**: a server sends no referrer, so Google refuses every request with 403 "Requests from referer <empty> are blocked" (seen 2026-10-28), and `match_youtube_artists` stops with an error.
3. Set `YOUTUBE_API_KEY` locally in `.env`, and on Render on the web service, then run a blueprint sync so the daily job gets it too. The client sends the key in the `X-goog-api-key` header, never in a URL.
4. Run `match_youtube_artists --dry-run --limit 10`, and check each proposed match on YouTube.
5. Run it for real, and review the matches at `/admin/core/youtubeartistlink/`.
6. Set `YOUTUBE_PREVIEWS` to `true` on the web service and in `.env`, then run `resave_all_events` so the stored event pages get their buttons.

**Quota:** a song search with its video check costs 101 units, so the daily step makes at most 90 searches (`--limit 90`). A Wikidata or MusicBrainz match costs 1 unit to check its channel, and so does each 30-day re-check. When the quota runs out, the run stops, keeps what it found, and the next morning's run carries on.

**What's stored:** for each name, only the YouTube channel ID and video ID, and which evidence matched them. YouTube's Developer Policies require stored data to be refreshed or deleted within 30 days, so every match is re-checked after 30 days. A video that's gone, or can no longer be embedded, loses its button. Links expire like the Spotify ones.

**Correcting a match:** paste a channel URL (`https://www.youtube.com/channel/UC…`), or a video URL (`watch?v=…` or `youtu.be/…`), or tick **No YouTube**. An editor's match shows its button even for an artist not matched on Spotify or Apple Music.

**The terms:**
- YouTube's Developer Policies require a privacy policy that says the site uses YouTube API Services and links to Google's Privacy Policy, and a link to YouTube's Terms of Service. `/privacy` does this, and every page's footer links to it.
- The Required Minimum Functionality rules forbid changing the player or putting anything over it, and require it to be at least 200 × 200 px. That's why custom-skin players such as csPlayer aren't used.

## Last.fm evidence

Last.fm is read behind the scenes, and nothing from it appears on the site.

**Shared names:** `resolve_artists_with_lastfm` settles names that several Spotify or Apple Music artists share, which the matching leaves "ambiguous". It reads the name's Last.fm page for its MusicBrainz ID, then MusicBrainz for that act's Spotify and Apple Music links. It matches the name to the linked artist only when MusicBrainz names the act as we do, links exactly one artist on that service, and the act is either:
- **local:** MusicBrainz's area, or the Last.fm bio, names a state or town where the site has venues;
- **dominant:** at least 100,000 Last.fm listeners, and a bio that doesn't say several acts share the name.

**How resolved links are kept:**
- **Marked "evidence":** the Spotify and Apple Music matching then treat them like an editor's link. They don't search for them or change their artist.
- **Re-checked monthly:** each one is checked again after 30 days, and set back to ambiguous if the evidence is gone.
- **Undo:** `resolve_artists_with_lastfm --revert` sets them all back. To review them, filter the links in the admin by source.

**YouTube songs:** `match_youtube_artists` searches YouTube for the most-played track on the name's Last.fm page, and checks its album, unless the page says several acts share the name (see "YouTube play buttons").

**Setting up the key:**
1. Create an API account at [last.fm/api/account/create](https://www.last.fm/api/account/create). Only the API key is used, not the secret.
2. Set `LASTFM_API_KEY` locally in `.env`, and on Render on the web service, then run a blueprint sync so the daily job gets it too.
3. Run `resolve_artists_with_lastfm --dry-run --limit 30`, and check the proposed matches.

Last.fm takes the key only as a URL parameter, so the client never prints or logs a request URL.

**The terms (last.fm/api/tos):**
- non-commercial use only;
- Last.fm credited, with a link;
- written approval for public pages that use the API;
- at most 100 MB of its data held at any time.

Nothing from Last.fm is displayed or stored, but its data decides which buttons appear, so ask before going public (see the launch checklist).

## Calendar feeds

`/calendar.ics` is an iCalendar feed that people can subscribe to in Google Calendar, Apple Calendar or Outlook. It takes the listing's `region`, `state` and `metro` parameters (for example `/calendar.ics?state=vermont`), and with none it covers the whole Northeast. It never uses a visitor's remembered filter.
- **What's in it:** approved shows from the past week through the next 90 days, with cancelled ones marked cancelled. Each show keeps the same ID in every feed and download (`event-<id>@newenglandmusic`), so a calendar app's refresh updates shows instead of duplicating them. That ID doesn't depend on the site's address, so moving to a custom domain is safe.
- **Refreshing:** the feed asks apps to refresh every six hours. Apple honours that; Google refreshes on its own schedule, up to about a day.
- **Caching:** responses carry an `ETag` and `Cache-Control: public, max-age=3600`, and an unchanged feed answers 304.
- **Subscribing:** a "Subscribe to this calendar" panel under the area filter offers a `webcal://` link, a Google Calendar link and the plain URL, all built from `SITE_URL`. Apple Calendar fetches `webcal://` over HTTPS, so locally (plain HTTP) subscribe to the `http://localhost:8001/calendar.ics?...` address instead. Set `SITE_URL` to the public address once there's a custom domain, or the links keep pointing at the `onrender.com` one.

## Saved shows and the event icons

Each event has a row of link icons below its text: calendar file, Google Calendar, map, share, and a bookmark to save the show. `/saved` lists a visitor's upcoming saved shows by date. Saved shows live only in the visitor's browser, in a `saved_shows` cookie of event IDs, so there are no accounts and nothing is stored on the server. The bookmark works without JavaScript too: it posts to `/saved/toggle/<id>`, which updates the cookie and goes back to the event.

The icon row is built when a page is rendered (`core/event_actions.py`), not stored with the event, so changing it needs no re-render. The stored HTML only holds a placeholder for it. After the deploy that introduced the placeholder (2026-10-27), run `resave_all_events` once on Render. Until then, stored events show no icon row.

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
- [ ] the API keys restricted: Places to its API, YouTube to YouTube Data API v3, Protomaps to the domain
- [ ] Last.fm asked (partners@last.fm) whether using its data only as matching evidence, with nothing displayed, needs its written approval or a credit, under its non-commercial terms.
- [ ] YouTube's Developer Policies met: `/privacy` linked from every page. The policies also say users must agree to the privacy policy before using the site. Decide whether a footer link is enough for a public listing.
- [x] the scheduled jobs added (the sheet's service account set up first): running on Render since 2026-10-26
- [ ] Eventbrite's API terms checked for attribution and caching rules, since events imported from it are shown on the site
- [ ] the first `fetch_events` run checked in `/admin/core/alleventproxy/` before events are approved
- [ ] **before announcing or sharing the site:** Google Places terms met. Until then, keep the site unshared. As of 2026-10-25 it was deployed but kept private for this reason.
  - **Stored content:** done. Only place IDs and coordinates are stored, and coordinates are refreshed or deleted within 30 days (see Google Places terms above). The daily `--refresh-stale` job has to be running for pins to stay exact.
  - **Maps (still open):** "Places API results displayed on a map must be shown on a Google Map". The day maps use Protomaps. The options: switch the day maps to the Google Maps JavaScript API, which has its own cost; pin venues from a geocoder whose results may be stored (US Census or OpenStreetMap) and use Places only for matching and the MAP link; or get a reading of the terms that allows the current maps. Each is a separate change.
