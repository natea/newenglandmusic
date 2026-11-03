## ADDED Requirements

### Requirement: Choices select shows
A subscriber's choices SHALL select an event when any one of them does. An **area** choice selects events at venues in that area, by the rules of `event-geo-filter`. A **followed town** selects events at venues in that town and state, ignoring case. A **followed venue** selects that venue's events. The "All of the Northeast" choice selects every area, and an area choice that no longer exists selects nothing.

#### Scenario: Area choice
- **WHEN** a subscriber's only choice is the Vermont area
- **THEN** the selected events are those at Vermont venues

#### Scenario: Followed town and venue
- **WHEN** a subscriber follows the town "Somerville, MA" and one venue in Portland, ME
- **THEN** events at venues in Somerville and at that venue are selected, and no others

### Requirement: Near a place selects by distance
A **near a place** choice SHALL select events at venues whose `exact_location` is within the chosen miles of the stored point, in a straight line. A venue with no coordinates SHALL never be selected by it.

#### Scenario: Distance choice
- **WHEN** a subscriber's choice is 10 miles from a point, and one venue is 6 miles away and another 14
- **THEN** only the first venue's events are selected

#### Scenario: Venue without coordinates
- **WHEN** a venue has no coordinates
- **THEN** a near-a-place choice does not select its events

### Requirement: Only approved events, once each
Only approved events SHALL be selected, and an event SHALL appear once however many choices select it.

#### Scenario: Union of choices
- **WHEN** an event is selected by both an area choice and a followed venue
- **THEN** it appears once

#### Scenario: Unapproved event
- **WHEN** an unapproved event is at a venue the choices select
- **THEN** it is not selected

### Requirement: What the weekly email holds
The email SHALL list the selected, uncancelled events that start from the start of the send day to the end of the seventh day after it, New York time, grouped by date in start order. Each SHALL show its title, artists, venue and town, start time, and a link to its event page at the site's own address (`/event/<id>`), never to the event's source. The email SHALL be plain text and HTML together, and SHALL carry the unsubscribe link and a link to sign in and change preferences.

#### Scenario: A week's shows
- **WHEN** the email is built for a send day and a subscriber's choices select shows on days 0, 3 and 8
- **THEN** the email lists the shows of days 0 and 3, grouped by date, and not day 8's

#### Scenario: Cancelled show
- **WHEN** a selected show is cancelled
- **THEN** the email leaves it out

#### Scenario: Both text and HTML
- **WHEN** the email is built
- **THEN** it has a plain-text part and an HTML part, each with the unsubscribe link

### Requirement: Event text is not trusted
The subject SHALL be fixed text, and all event text SHALL be escaped in the HTML part.

#### Scenario: Markup in a title
- **WHEN** an event's title holds `<script>`
- **THEN** the HTML part shows it as text and the subject is unchanged

### Requirement: A limit on the length
The email SHALL show at most 50 events. When more are selected, it SHALL end with a link to the site's listing filtered to the first area choice, or to the whole listing when there is none.

#### Scenario: More than the limit
- **WHEN** 60 shows are selected
- **THEN** the email lists the first 50 by start time and ends with a link to see all of them on the site

### Requirement: Sending once a week
The command `send_weekly_digests` SHALL be recorded as a `JobRun` and SHALL send one email to each confirmed, unpaused subscriber once per send week. It SHALL skip a subscriber with no selected shows in the window and one already sent this week, so a second run sends nothing. It SHALL take `--dry-run`, which builds every email and sends none, and `--limit`. A scheduled job SHALL run it weekly.

#### Scenario: Confirmed subscriber with shows
- **WHEN** the command runs for a confirmed subscriber who has selected shows
- **THEN** one email is sent and the subscriber's last-sent week is recorded

#### Scenario: Nothing to send
- **WHEN** a confirmed subscriber has no selected shows in the window
- **THEN** no email is sent, and the run's summary counts them as skipped

#### Scenario: Run twice
- **WHEN** the command runs twice in the same week
- **THEN** each subscriber gets at most one email

#### Scenario: Paused or unconfirmed
- **WHEN** a subscriber is paused, or has not confirmed
- **THEN** no email is sent to them

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** no email is sent and no last-sent week is recorded

### Requirement: Sends are claimed and paced
The command SHALL claim a subscriber for the week before sending, so two overlapping runs can't both send, and SHALL release the claim if the send fails. It SHALL pace sends within the mail account's rate and treat a throttling reply as a failed send to retry on the next run.

#### Scenario: Overlapping runs
- **WHEN** two runs start together
- **THEN** each subscriber is sent one email

### Requirement: A failed send does not stop the rest
One subscriber's failed send SHALL be logged without the address and SHALL NOT stop the others. The command SHALL fail the run if any send failed, and the failed subscriber SHALL be tried again on the next run in the same week.

#### Scenario: One send fails
- **WHEN** the mail service rejects one subscriber's email
- **THEN** the others are still sent, the run is marked failed, the log names no address, and the failed subscriber is tried again on the next run

### Requirement: Mail carries the headers readers expect
Each weekly email, confirmation email and sign-in code email SHALL be built as a MIME message that refuses line breaks in headers and sent through the site's mail sender as a raw message. The weekly email SHALL hold an HTTPS `List-Unsubscribe` header and `List-Unsubscribe-Post: List-Unsubscribe=One-Click`.

#### Scenario: Unsubscribe headers
- **WHEN** a weekly email is sent
- **THEN** the raw message has `List-Unsubscribe` with the subscriber's signed unsubscribe address and `List-Unsubscribe-Post`

#### Scenario: Confirmation and code emails
- **WHEN** a confirmation email and a sign-in code email are sent
- **THEN** each is sent as a raw multipart text and HTML message, with no unsubscribe headers

#### Scenario: Line break in an address
- **WHEN** an address holds a line break
- **THEN** no message is built

### Requirement: Sending fails loudly when not set up
Nothing SHALL be sent from the placeholder `webmaster@localhost` sender, nor while the site address (`SITE_URL`) is not an `https://` address or is localhost, because every link in the email would be dead. When the mail service has no credentials or the sender is unset, sending SHALL fail with a clear error in the log rather than silently dropping the message.

#### Scenario: Mail service not configured
- **WHEN** a send is attempted with no mail service credentials
- **THEN** the failure is logged and the command's run is marked failed

#### Scenario: Sender unset
- **WHEN** `DEFAULT_FROM_EMAIL` is the placeholder `webmaster@localhost`
- **THEN** nothing is sent and the failure is logged

#### Scenario: Site address unset
- **WHEN** `SITE_URL` is blank, falls back to localhost, or is not an `https://` address
- **THEN** nothing is sent, the failure is logged and the command's run is marked failed

