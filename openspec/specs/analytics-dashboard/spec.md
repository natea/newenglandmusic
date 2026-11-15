# analytics-dashboard Specification

## Purpose
Gives the editors one PostHog dashboard of how the site is used, defined in the repo so its charts are reviewed like code and kept in step with PostHog by a command.

## Requirements

### Requirement: The dashboard is defined in the repo
The dashboard's name, description and charts SHALL be defined in the repo, each chart with a stable key, a name, a description saying what question it answers, and the PostHog query it runs. Every chart SHALL use only events and properties the site sends, or PostHog's own pageview and GeoIP properties.

#### Scenario: Charts use sent events
- **WHEN** the chart definitions are checked
- **THEN** every event a chart names is one the site sends (site-analytics) or one of PostHog's own (`$pageview`, `$pageleave`), and every chart has a key, a name and a description

### Requirement: A command keeps PostHog's dashboard in step
`sync_posthog_dashboard` SHALL create the dashboard in the configured PostHog project when it doesn't exist, and otherwise update it: creating charts that are new, updating charts that changed, and removing from the dashboard charts it made that are no longer defined, recognising its own charts by their key. Running it twice SHALL change nothing the second time. `--dry-run` SHALL print what it would do and change nothing.

#### Scenario: First run
- **WHEN** the command runs and no dashboard of that name exists
- **THEN** it creates the dashboard and every chart on it

#### Scenario: A chart changed
- **WHEN** a chart's definition changes and the command runs again
- **THEN** that chart is updated in place, and no other chart changes

#### Scenario: A chart removed
- **WHEN** a chart is removed from the definitions and the command runs
- **THEN** the chart the command made for it is deleted, and charts it didn't make are left alone

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it lists the dashboard and charts it would create, update or delete, and sends no change to PostHog

### Requirement: The wizard's empty dashboard is removed
The command SHALL delete the PostHog wizard's "Analytics basics (wizard)" dashboard and the charts on it, which chart server-side events the site doesn't send, and SHALL leave any other dashboard alone.

#### Scenario: The wizard's dashboard
- **WHEN** the command runs and the wizard's dashboard exists
- **THEN** it's deleted, with its charts, and other dashboards are untouched

### Requirement: The API key stays secret and narrow
The command SHALL read a personal API key from `POSTHOG_PERSONAL_API_KEY` and send it only in the `Authorization` header to the configured PostHog app host. The key SHALL never appear in a URL, a log line, the command's output or an error message. Without the key, the command SHALL stop with a message saying which setting is missing, and change nothing.

#### Scenario: No key
- **WHEN** the command runs without `POSTHOG_PERSONAL_API_KEY`
- **THEN** it stops saying the key is missing, and makes no request

#### Scenario: A failed request
- **WHEN** PostHog answers a request with an error
- **THEN** the command stops with the status and PostHog's message, and the output holds no key
