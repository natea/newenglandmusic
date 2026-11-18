## ADDED Requirements

### Requirement: Each pull request that changes code gets a preview

When a pull request against `main` that changes a file outside `openspec/` and `docs/` is opened, Render SHALL deploy a preview of the site right away, before any merge: the web service and a database of its own, at an address of their own. A push to the pull request SHALL redeploy the preview. A pull request that changes only files under `openspec/` or `docs/` SHALL get no preview. A pull request whose title holds `[skip preview]` SHALL get none either.

#### Scenario: A build's pull request

- **WHEN** the loop opens a pull request from `change/improve-band-discovery` that changes `core/views.py`
- **THEN** Render deploys a preview of the site for it, at its own `onrender.com` address, and reports the deploy on the pull request

#### Scenario: A draft proposal's changes only

- **WHEN** a pull request changes only files under `openspec/changes/`
- **THEN** no preview is made

#### Scenario: A new push

- **WHEN** a commit is pushed to a pull request that has a preview
- **THEN** the preview is redeployed with it, and keeps its database

### Requirement: A preview ends with its pull request

Render SHALL delete a preview, its web service and its database, when its pull request is merged or closed, or after 7 days without a push to it.

#### Scenario: Merged

- **WHEN** a pull request with a preview is merged
- **THEN** its preview and its database are deleted

#### Scenario: Idle

- **WHEN** nothing is pushed to an open pull request for 7 days
- **THEN** its preview and its database are deleted, and the next push makes a new one

### Requirement: A preview's database starts as a cleaned copy of the live data

After a preview's first deploy, its database SHALL hold the live site's venues, acts, events, their links and stored pages, and the site's pages, as they are at that moment, with the pull request's migrations applied on top. A later redeploy SHALL keep the preview's data.

#### Scenario: Seeded

- **WHEN** a preview finishes its first deploy
- **THEN** its listing shows the same events, venues and acts as the live site

#### Scenario: A pull request with a migration

- **WHEN** the pull request adds a migration
- **THEN** the preview's database has the live data with that migration applied, and the live database is unchanged

### Requirement: People's data never reaches a preview

The copy SHALL leave out every subscriber, sign-in code, weekly-email choice, mail request and session. Each admin account's email SHALL be replaced and its password made unusable, and every event's submitter email SHALL be emptied, before the preview's address is given to anyone.

#### Scenario: People-only tables

- **WHEN** the seed is done
- **THEN** the preview has no subscribers, sign-in codes, weekly-email choices, mail requests or sessions

#### Scenario: Personal fields

- **WHEN** the seed is done
- **THEN** no admin account has its live email or a usable password, and no event has a submitter email

#### Scenario: The seed fails

- **WHEN** the copy from the live database fails
- **THEN** the seed fails with the reason in the deploy's log, and the preview's database holds nothing from the live site

### Requirement: The live data is only read

The seed SHALL connect to the live database only as a role that can read and not write. Nothing a preview does SHALL change the live database.

#### Scenario: Something saved on a preview

- **WHEN** a reviewer saves a venue in a preview's admin
- **THEN** the change is in the preview's database only, and the live site doesn't show it

### Requirement: A preview has its own admin

The seed SHALL create one admin account, `preview-admin`, with the password set for previews only. No live account SHALL be able to sign in to a preview.

#### Scenario: Nate checks an admin change

- **WHEN** Nate signs in to a preview's admin as `preview-admin`
- **THEN** he is signed in, and can see and change the preview's data

### Requirement: A preview never reaches the outside world

A preview SHALL send no email, and SHALL hold no key for an outside API, the analytics or the sheet sync. Its scheduled jobs SHALL NOT exist: the daily, weekly and weekly-email jobs are left out of previews. The play buttons stored in event pages SHALL still show.

#### Scenario: Signing up for the weekly email

- **WHEN** a reviewer asks for the weekly email on a preview
- **THEN** no email is sent, and the preview's log notes that mail isn't set up, without the address, as the site does today when the sender isn't set

#### Scenario: No jobs

- **WHEN** a preview exists
- **THEN** no daily, weekly or weekly-email job runs for it

#### Scenario: A stored play button

- **WHEN** a reviewer opens an event with a Spotify play button stored in its page
- **THEN** the button shows as on the live site
