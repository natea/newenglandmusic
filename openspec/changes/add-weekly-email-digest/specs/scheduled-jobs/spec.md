## MODIFIED Requirements

### Requirement: The jobs are scheduled on the host with the site's keys
The host configuration SHALL define a daily job, a weekly job and a weekly digest job, the weekly job running before the daily run on the same day. Each SHALL get the database and the API keys its commands need from the web service and the database, so each key is set in one place. The jobs SHALL NOT run migrations.

#### Scenario: Configuration
- **WHEN** `render.yaml` is read
- **THEN** it defines the three cron jobs with their schedules and scripts, each lists the keys its commands use from the web service, and no job's build runs migrations

## ADDED Requirements

### Requirement: A digest job sends the weekly email
The host configuration SHALL define a job, run weekly, that runs `send_weekly_digests` through a script that reports failure as the other jobs' scripts do. It SHALL copy the settings it needs, including the mail credentials, from the web service, where each is declared. It SHALL NOT run migrations.

#### Scenario: Digest job configuration
- **WHEN** the host configuration is read
- **THEN** it defines a weekly job whose start command runs `send_weekly_digests`, with those settings taken from the web service, and no migration step
