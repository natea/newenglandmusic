## ADDED Requirements

### Requirement: No whole-database export route
The site SHALL NOT serve any route that returns its events, venues or pages as a bulk export for a caller holding a shared token. The path `/internal-api/db` SHALL answer 404 to every request.

#### Scenario: Export path answers 404 with a token
- **WHEN** a client requests `/internal-api/db` with an `Authorization: Bearer` header carrying any value, including `unused`
- **THEN** the response status is 404 and no event, venue or page data is returned

#### Scenario: Export path answers 404 without a token
- **WHEN** a client requests `/internal-api/db` with no `Authorization` header
- **THEN** the response status is 404, not 401

#### Scenario: Export route is not registered
- **WHEN** the URL name `internal_db_dump` is reversed
- **THEN** Django raises `NoReverseMatch`

### Requirement: No command copies data from another site
The project SHALL NOT include a management command that copies events, venues or pages from another site's export endpoint.

#### Scenario: Command no longer exists
- **WHEN** `populate_data_from_prod` is run through `manage.py`
- **THEN** Django reports an unknown command

### Requirement: Site starts without the inherited export settings
The site SHALL start, and its tests SHALL pass, without `RC_DEVELOPER_INTERNAL_TOKEN` or `PROD_INTERNAL_API_SERVER` in the environment, and the settings SHALL NOT read or define them.

#### Scenario: Settings load with the variables unset
- **WHEN** the settings module is loaded with neither variable in the environment
- **THEN** loading succeeds and the settings define neither `RC_DEVELOPER_INTERNAL_TOKEN` nor `PROD_INTERNAL_API_SERVER`

### Requirement: Configuration files do not set the inherited export settings
No file in the repository that configures an environment (`render.yaml`, `.env.example`, CI and build workflow files) or documents configuration SHALL set or mention `RC_DEVELOPER_INTERNAL_TOKEN` or `PROD_INTERNAL_API_SERVER`, and none SHALL keep a fixed token value.

#### Scenario: No file mentions the settings
- **WHEN** the repository is searched, outside archived OpenSpec changes and this change's own files, for either variable name
- **THEN** there are no matches
