# StageHopper

[![Django CI](https://github.com/natea/newenglandmusic/actions/workflows/django.yml/badge.svg)](https://github.com/natea/newenglandmusic/actions/workflows/django.yml)

**Live music across New England.** [stagehopper.app](https://stagehopper.app)

StageHopper is a calendar of live music in Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine and Vermont. It covers the big ticketed halls, and also the bars, cafés, breweries, listening rooms and DIY spaces that the big show apps miss. It's built around a list of about 730 venues, curated by people who know the scene, and it serves two audiences equally:

- **Fans** deciding what to see this week, near them.
- **Musicians**, local and touring, looking for rooms that book acts like theirs.

It's a community resource: no ads, no paid placement.

## What it does

- **A calendar of shows**, day by day, filtered by state, metro area, town or Boston neighborhood, with how far each show is from you.
  - **Saved shows:** bookmark shows; they're kept in your browser, with no account needed.
  - **Calendar feeds:** subscribe to the shows in your area from your own calendar app.
  - **The weekly email:** this week's shows in your area, each Monday (opening to everyone once its email sending is approved).
- **Play buttons** on each listing, to hear an act before you go: Spotify, Apple Music, YouTube or Bandcamp, through each service's own player.
- **Band and artist pages,** with members, links, a credited Wikipedia introduction and every upcoming show, plus an A–Z index at [/bands](https://stagehopper.app/bands).
- **Band discovery:** a deck of acts playing near you soon, one card at a time, to listen to and save.
- **Search** across bands, venues and shows.

On their way (open pull requests):
- a page for every event;
- a page for every venue, showing its upcoming shows as the room's own bill;
- a venue list with a "For artists" view of how to book each room.

## How it works

Editors keep the venue list in the Django admin. Every day, scheduled jobs fetch each venue's upcoming shows, from whichever source the venue has:
- ticketing APIs (Ticketmaster, Eventbrite, SeatGeek);
- the venue's own calendar feed or event pages;
- AI extraction from its website, for venues with nothing structured.

New events wait for an editor's approval before they're published. Acts named on approved events are matched to band and artist records (MusicBrainz, Wikidata, Wikipedia) and to their Spotify, Apple Music, YouTube and Bandcamp players, always on evidence. Editors can correct any match in the admin.

The details:

| Doc | What's in it |
|---|---|
| [PRODUCTION.md](PRODUCTION.md) | Deployment and every scheduled job |
| [AGENTS.md](AGENTS.md) | Working on the code: setup, the pipeline, data sources, paid APIs, conventions |
| [DESIGN.md](DESIGN.md) | The visual design |
| [openspec/specs](openspec/specs) | What each part of the site does |

Changes are proposed and reviewed as [OpenSpec](https://github.com/Fission-AI/OpenSpec) changes before they're built. [docs/SPEK.md](docs/SPEK.md) and [docs/FABRO.md](docs/FABRO.md) describe that workflow and the agents that help with it.

## Running it locally

You'll need Python 3.11, [uv](https://docs.astral.sh/uv/) and Postgres.

```bash
uv venv venv --python 3.11
uv pip install --python venv/bin/python -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # API keys are optional for browsing; see AGENTS.md
venv/bin/python manage.py migrate
venv/bin/python manage.py compilescss
venv/bin/python manage.py runserver 8001
```

Tests:

```bash
venv/bin/python -m playwright install chromium   # once, for the browser tests
venv/bin/python manage.py test
```

The tests never touch the network: every outside service is mocked.

## Data and credits

StageHopper shows only what each source's terms allow, and credits it where it's shown:
- **Wikipedia** introductions: CC BY-SA 4.0.
- **MusicBrainz** genres: CC BY-NC-SA.
- **Neighborhoods:** © OpenStreetMap contributors.
- **Town lookups:** the US Census Bureau's Gazetteer files, which are public domain.
- **Players:** Spotify, Apple Music, YouTube and Bandcamp, through their own embeds.

StageHopper is run by Jazkarta, Inc.

## Where it came from

StageHopper began as a fork of **[nyc noise](https://nyc-noise.com/)**, Jessica Hallock's digital cultural calendar for New York City, and owes it both the idea and the first codebase. A calendar should be friendly, fast and maintained by people who care about the scene: StageHopper takes that from nyc noise and brings it to New England.

In late 2023, a group from [the Recurse Center](https://www.recurse.com/) rebuilt nyc noise from its WordPress original into the Django app this repository grew from. It launched on December 6, 2023. Its source is at [nycnoise/nycnoise](https://github.com/nycnoise/nycnoise).

Since the fork, StageHopper's data, scope and features have diverged on purpose, but its foundations are theirs. These are the people who built nyc noise's code and documentation, listed with [All Contributors](https://allcontributors.org/):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/SwantjeM"><img src="https://avatars.githubusercontent.com/u/28712729?v=4?s=100" width="100px;" alt="SwantjeM"/><br /><sub><b>SwantjeM</b></sub></a><br /><a href="#doc-SwantjeM" title="Documentation">📖</a> <a href="#code-SwantjeM" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/gregsadetsky"><img src="https://avatars.githubusercontent.com/u/1017304?v=4?s=100" width="100px;" alt="Greg Sadetsky"/><br /><sub><b>Greg Sadetsky</b></sub></a><br /><a href="#doc-gregsadetsky" title="Documentation">📖</a> <a href="#code-gregsadetsky" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/42lucasbezerra"><img src="https://avatars.githubusercontent.com/u/50885067?v=4?s=100" width="100px;" alt="Lucas Bezerra"/><br /><sub><b>Lucas Bezerra</b></sub></a><br /><a href="#code-42lucasbezerra" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://evanconway.github.io/#/"><img src="https://avatars.githubusercontent.com/u/43253820?v=4?s=100" width="100px;" alt="Evan Conway"/><br /><sub><b>Evan Conway</b></sub></a><br /><a href="#doc-evanconway" title="Documentation">📖</a> <a href="#code-evanconway" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/andrea749"><img src="https://avatars.githubusercontent.com/u/20407254?v=4?s=100" width="100px;" alt="Andrea Garcia"/><br /><sub><b>Andrea Garcia</b></sub></a><br /><a href="#code-andrea749" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/robsimmons"><img src="https://avatars.githubusercontent.com/u/442315?v=4?s=100" width="100px;" alt="Robert J. Simmons"/><br /><sub><b>Robert J. Simmons</b></sub></a><br /><a href="#code-robsimmons" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://nyc-noise.com"><img src="https://avatars.githubusercontent.com/u/135757981?v=4?s=100" width="100px;" alt="nyc noise"/><br /><sub><b>nyc noise</b></sub></a><br /><a href="#code-nycnoise" title="Code">💻</a></td>
    </tr>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/reyaw"><img src="https://avatars.githubusercontent.com/u/82685635?v=4?s=100" width="100px;" alt="Reya Wallace"/><br /><sub><b>Reya Wallace</b></sub></a><br /><a href="#code-reyaw" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/astrano"><img src="https://avatars.githubusercontent.com/u/291487?v=4?s=100" width="100px;" alt="Alison Strano"/><br /><sub><b>Alison Strano</b></sub></a><br /><a href="#code-astrano" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/litviakk"><img src="https://avatars.githubusercontent.com/u/12960880?v=4?s=100" width="100px;" alt="litviakk"/><br /><sub><b>litviakk</b></sub></a><br /><a href="#code-litviakk" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="http://www.kaleballmon.com"><img src="https://avatars.githubusercontent.com/u/56810618?v=4?s=100" width="100px;" alt="Kaleb Allmon"/><br /><sub><b>Kaleb Allmon</b></sub></a><br /><a href="#code-kaleballmon" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/skeryl"><img src="https://avatars.githubusercontent.com/u/3475474?v=4?s=100" width="100px;" alt="Shane"/><br /><sub><b>Shane</b></sub></a><br /><a href="#code-skeryl" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/vivngo"><img src="https://avatars.githubusercontent.com/u/9523397?v=4?s=100" width="100px;" alt="Vivien Ngo"/><br /><sub><b>Vivien Ngo</b></sub></a><br /><a href="#code-vivngo" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->
