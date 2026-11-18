## ADDED Requirements

### Requirement: A cleaned copy of the live data is kept for previews

Once a night, the live data SHALL be copied into the previews' base database through a role that can only read. The copy SHALL hold the live site's venues, acts, events, their links and stored pages, and the site's pages. A failed copy SHALL leave the previous night's copy in place.

#### Scenario: The nightly copy

- **WHEN** the nightly copy finishes
- **THEN** the base database has the live site's events, venues and acts

#### Scenario: The copy fails

- **WHEN** reading the live database fails during the nightly copy
- **THEN** the job fails with the reason in its log, and previews keep branching from the previous copy

### Requirement: People's data never reaches the copy

The copy SHALL leave out every subscriber, sign-in code, weekly-email choice, mail request and session. Each admin account's email SHALL be replaced and its password made unusable, and every event's submitter email SHALL be emptied, before any preview can branch from the copy.

#### Scenario: People-only tables

- **WHEN** the nightly copy finishes
- **THEN** the base database has no subscribers, sign-in codes, weekly-email choices, mail requests or sessions

#### Scenario: Personal fields

- **WHEN** the nightly copy finishes
- **THEN** no admin account has its live email or a usable password, and no event has a submitter email

### Requirement: Each pull request that changes code gets a preview

When a pull request against `main` from a branch of this repository, changing a file outside `openspec/` and `docs/`, is opened or reopened, a preview of the site SHALL be deployed right away, before any merge, on a copy of the base, and reported to GitHub as a deployment of `preview-pr-<number>`. A pull request from a fork, or one changing only `openspec/` or `docs/`, SHALL get no preview.

#### Scenario: A build's pull request

- **WHEN** the loop opens pull request 73 from `change/improve-band-discovery`, changing `core/views.py`
- **THEN** a preview is deployed for it, and GitHub shows a successful deployment of `preview-pr-73` with the preview's address

#### Scenario: Changes to specs only

- **WHEN** a pull request changes only files under `openspec/changes/`
- **THEN** no preview is made

#### Scenario: A pull request from a fork

- **WHEN** someone opens a pull request from their own fork of the repository
- **THEN** no preview is made, and no secret is used

### Requirement: A preview runs the pull request's code on its own data

A preview's database SHALL start as a copy of the base, with the pull request's migrations applied. A push to the pull request SHALL redeploy its code and apply any new migrations on the same database, keeping what was saved on the preview. Nothing a preview does SHALL change the live database.

#### Scenario: A pull request with a migration

- **WHEN** the pull request adds a migration
- **THEN** the preview's database has the base data with that migration applied, and the live database is unchanged

#### Scenario: A new push

- **WHEN** a commit is pushed to a pull request with a preview
- **THEN** the preview runs the new code, and a venue saved on the preview before the push is still there

#### Scenario: Something saved on a preview

- **WHEN** a reviewer saves a venue in a preview's admin
- **THEN** the live site doesn't show it

### Requirement: A preview ends with its pull request

When a pull request is merged or closed, its preview and its database SHALL be deleted and its deployment marked inactive. Once a day, any preview whose pull request has had no push for 7 days, or is no longer open, SHALL be deleted too. A later push SHALL make a new preview.

#### Scenario: Merged

- **WHEN** a pull request with a preview is merged
- **THEN** its preview and its database are deleted, and its deployment shows as inactive

#### Scenario: Idle

- **WHEN** nothing is pushed to an open pull request for 7 days
- **THEN** the daily sweep deletes its preview and database, and the next push makes a new one

### Requirement: A preview has its own admin

Each preview SHALL have one admin account, `preview-admin`, with the password kept for previews only. No live account SHALL be able to sign in to a preview.

#### Scenario: Nate checks an admin change

- **WHEN** Nate signs in to a preview's admin as `preview-admin`
- **THEN** he is signed in and can see and change the preview's data

### Requirement: A preview never reaches the outside world

A preview SHALL send no email, and SHALL hold no key for an outside API, the analytics or the sheet sync. No scheduled job SHALL run for a preview. Every page of a preview SHALL ask search engines not to index it. The play buttons stored in event pages SHALL still show.

#### Scenario: Signing up for the weekly email

- **WHEN** a reviewer asks for the weekly email on a preview
- **THEN** no email is sent, and the preview's log notes that mail isn't set up, without the address

#### Scenario: Not indexed

- **WHEN** any page of a preview is requested
- **THEN** the response carries `X-Robots-Tag: noindex, nofollow`

#### Scenario: A stored play button

- **WHEN** a reviewer opens an event with a Spotify play button stored in its page
- **THEN** the button shows as on the live site
