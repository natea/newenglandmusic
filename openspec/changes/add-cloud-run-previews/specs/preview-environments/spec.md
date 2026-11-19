## ADDED Requirements

### Requirement: A cleaned copy of the live data is kept for previews

Once a night, the live data SHALL be copied into the previews' base database, read through a role that can only read. The copy SHALL hold every table of the live site that isn't people's data, as it is that night. A failed copy SHALL leave the previous night's copy in place.

#### Scenario: The nightly copy

- **WHEN** the nightly copy finishes
- **THEN** the base database has the live site's events, venues, acts and pages

#### Scenario: The copy fails

- **WHEN** reading the live database fails during the nightly copy
- **THEN** the job fails with the reason in its log, and previews keep branching from the previous copy

#### Scenario: A role that can write

- **WHEN** the nightly copy is given a role that may write to the live database
- **THEN** it refuses to start, naming the role

### Requirement: People's data never reaches the copy

The data SHALL be cleaned before it is loaded into the base database, so nothing uncleaned is ever stored where previews are. The cleaned copy SHALL have no subscriber of either kind, sign-in code, weekly-email choice, mail request, session, admin change log entry or account from the live site, no submitter email on any event, and no stored output or error of a job run.

#### Scenario: People-only tables

- **WHEN** the nightly copy finishes
- **THEN** the base database has no subscribers, sign-in codes, weekly-email choices, mail requests, sessions or admin change log entries

#### Scenario: Personal fields

- **WHEN** the nightly copy finishes
- **THEN** the base database has no account from the live site, no event with a submitter email, and no job run with stored output or an error

#### Scenario: Cleaned before it is stored

- **WHEN** the cleaning step fails
- **THEN** nothing is loaded into the base database

### Requirement: Every table is classified

Each table of the site SHALL be listed as copied, cleaned or left out. The site's tests SHALL fail while a table is on no list, so a new table can't reach previews unconsidered.

#### Scenario: A new table

- **WHEN** a migration adds a table that is on none of the lists
- **THEN** the site's tests fail, naming the table

### Requirement: Each pull request that changes code gets a preview

When a pull request against `main` from a branch of this repository, changing a file outside `openspec/` and `docs/`, is opened or reopened, or gains such a change by a push, a preview of the site SHALL be deployed on a copy of the base and reported to GitHub as a successful deployment of `preview-pr-<number>` with its address. A pull request from a fork, one of Dependabot's, or one changing only `openspec/` or `docs/`, SHALL get no preview.

#### Scenario: A build's pull request

- **WHEN** the loop opens pull request 73 from `change/improve-band-discovery`, changing `core/views.py`
- **THEN** a preview is deployed for it, and GitHub shows a successful deployment of `preview-pr-73` with the preview's address

#### Scenario: Reopened

- **WHEN** pull request 73 is reopened after its preview was removed
- **THEN** a new preview is deployed for it

#### Scenario: Changes to specs only

- **WHEN** a pull request changes only files under `openspec/changes/`
- **THEN** no preview is made

#### Scenario: A pull request from a fork

- **WHEN** someone opens a pull request from their own fork of the repository
- **THEN** no preview is made, and no secret is used

#### Scenario: Dependabot

- **WHEN** Dependabot opens a pull request
- **THEN** no preview is made

#### Scenario: Every slot in use

- **WHEN** a pull request opens while every preview slot holds an open pull request's preview
- **THEN** no preview is made, and the pull request's check fails saying the limit is reached

#### Scenario: A slot held by a closed pull request

- **WHEN** a pull request opens while every slot is taken and one holds the preview of a pull request closed without merging
- **THEN** that preview is removed, the one pushed to longest ago if there are several, and the new pull request gets its preview

### Requirement: A preview runs the pull request's code on its own data

A preview's database SHALL start as a copy of the base, with the pull request's migrations applied. A push to the pull request SHALL redeploy its code and apply any new migrations on the same database, keeping what was saved on the preview. When the migrations can't be applied to the kept database, the preview SHALL start again from the base. Nothing a preview does SHALL change the live database.

#### Scenario: A pull request with a migration

- **WHEN** the pull request adds a migration
- **THEN** the preview's database has the base data with that migration applied, and the live database is unchanged

#### Scenario: A new push

- **WHEN** a commit is pushed to a pull request with a preview
- **THEN** the preview runs the new code, and a venue saved on the preview before the push is still there

#### Scenario: A migration rewritten

- **WHEN** a push replaces a migration the preview already applied, and the new ones fail on the kept database
- **THEN** the preview's database is made again from the base with the pull request's migrations, and the deploy succeeds

#### Scenario: Something saved on a preview

- **WHEN** a reviewer saves a venue in a preview's admin
- **THEN** the live site doesn't show it

### Requirement: A preview ends on merge or when idle

When a pull request is merged, its preview and database SHALL be deleted and its deployments marked inactive. Once a day, the preview of an open pull request with no push for 7 days SHALL be deleted and its deployments marked inactive, as SHALL any whose pull request no longer exists. A pull request closed without merging SHALL keep its preview until its slot is needed. A removed preview SHALL be made again by a later push, or by hand.

#### Scenario: Merged

- **WHEN** a pull request with a preview is merged
- **THEN** its preview and its database are deleted, and its deployments show as inactive

#### Scenario: Closed without merging

- **WHEN** a pull request with a preview is closed without merging, and 30 days pass with slots free
- **THEN** its preview is still there

#### Scenario: Idle

- **WHEN** nothing is pushed to an open pull request for 7 days
- **THEN** the daily sweep deletes its preview and database and marks its deployments inactive

#### Scenario: Rebuilt by hand

- **WHEN** Nate runs the preview workflow for pull request 73 after its preview was swept
- **THEN** a new preview is deployed for it, from the base

### Requirement: A preview has its own admin

Each preview SHALL have one account, `preview-admin`, an admin with the password kept for previews. No account from the live site SHALL exist on a preview.

#### Scenario: Signing in as the preview admin

- **WHEN** Nate signs in to a preview's admin as `preview-admin`
- **THEN** he is signed in and can see and change the preview's data

#### Scenario: A live account

- **WHEN** someone tries a live admin's username and password on a preview
- **THEN** they aren't signed in

### Requirement: A preview never reaches the outside world

A preview SHALL send no email, and SHALL hold no key for an outside API, the analytics or the sheet sync that works: its player settings are placeholders that only switch the players on, so its pages show players as the live site does. No scheduled job SHALL run for a preview. The site's data-export endpoint SHALL answer 404 on a preview. Every response of a preview SHALL ask search engines not to index it. The play buttons stored in event pages SHALL still show.

#### Scenario: Signing up for the weekly email

- **WHEN** a reviewer asks for the weekly email on a preview
- **THEN** no email is sent, and the preview's log notes that mail isn't set up, without the address

#### Scenario: What a preview is given

- **WHEN** a preview is deployed
- **THEN** its settings are exactly the listed ones: its database, its own secret key, the preview settings, and the player settings

#### Scenario: No jobs

- **WHEN** a preview exists
- **THEN** nothing runs the daily, weekly or weekly-email job for it

#### Scenario: The data export

- **WHEN** `/internal-api/db` is requested on a preview, with any token
- **THEN** the answer is 404

#### Scenario: Not indexed

- **WHEN** any page or static file of a preview is requested
- **THEN** the response carries `X-Robots-Tag: noindex, nofollow`

#### Scenario: Players on a preview

- **WHEN** a reviewer opens the discovery deck or an event page on a preview
- **THEN** the players show as on the live site

#### Scenario: A stored play button

- **WHEN** a reviewer opens the listing with an event whose saved page has a Spotify play button
- **THEN** the button shows as on the live site
