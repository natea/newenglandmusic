Issue: [#13 Visitors can signup to receive a weekly email of upcoming shows that match their interests](https://github.com/natea/newenglandmusic/issues/13)

## Context

What the site does today:

- **No visitor accounts.** Django's `auth`, `sessions` and `admin` are installed, but only editors have logins. Visitors keep their saved shows, area filter and location in cookies, and the privacy page says the site stores nothing about them.
- **Area filtering** lives in `core/geo_filters.py`: `GeoFilter` and `area_q()` turn region, state and metro slugs (plus a metro's towns) into a query on `Venue` fields, and `/calendar.ics` already uses them for subscriptions.
- **Distance** lives in `core/location.py`: `resolve()` turns a ZIP code or town into a `Location` or a list of candidates, `rounded()` keeps three decimal places, and `miles()` measures. Venues expose `exact_location`, the Google Places point when confident, else the sheet's coordinates.
- **Email.** `core/utils_aws.py` has an Amazon SES sender (`aws_mail_sender`) that sends a simple message with no custom headers. It is used by `test_email` and by event-submission notifications. An older `EmailSubscriber` model and `/email-subscribe` view exist from the upstream project; the signup form is commented out of the homepage template and nothing sends to those addresses.
- **Scheduling.** Render cron jobs run `bin/daily.sh` and `bin/weekly.sh`; commands based on `RecordedCommand` appear in the job history.
- **Venues have no public page or slug yet** (`add-venue-pages` is proposed, not built), so a followed venue is stored by its database id.

The thread settled: a placeholder account made from just an email address, passwordless sign-in by emailed code, all three place-choice styles, one weekly email in this version, and later possibilities (text messages, band following, daily or several emails) left out.

## Goals / Non-Goals

**Goals:**
- A visitor gets a useful weekly email after giving only an email address and choosing places.
- Leaving is always one step away; nothing is sent without a confirmed address.
- The choices reuse the area and distance code the listing already has.

**Non-Goals:**
- Genre choices (need a genre selector; separate proposal), text messages, band or artist following, daily emails, several emails per subscriber.
- Email to the old `EmailSubscriber` addresses.
- Visitor login for anything but this email.

## Decisions

### A separate `Subscriber` model, not a Django `User`
The "account" is a `Subscriber` row: `email` (unique, stored lowercase), `confirmed_at`, `paused`, `created_at`, `last_digest_week` (the Monday of the last week sent, as a date). Making visitors Django users would put thousands of strangers in the same table as editors, one `is_staff` mistake from the admin. A separate model keeps editors and subscribers apart, costs nothing extra, and a later move to real accounts (for following bands) can link a subscriber to a user then.

### Passwordless sign-in with a hashed code
`SignInCode` rows hold `subscriber`, a hash of the 6-digit code (an HMAC with the site's secret key, compared in constant time, so a leaked table can't be reversed by trying all million codes; the code comes from `secrets`), `created_at`, `used_at` and `attempts`. Rules: 15 minutes, single use, a new code cancels older ones, locked after 5 wrong tries on one code and after 10 in an hour for one address, and at most 3 confirmation, already-subscribed or code emails an hour per address (counted from a small `MailRequest` log of address and time, deleted after a day; the table exists only for these limits, see open question 5). Signup and sign-in requests are also limited to 10 an hour per client, counted in the same table by a hash of the client address taken from the last entry of `X-Forwarded-For`, which the host appends and the visitor can't set (the leftmost entries can be forged); the setting is read in one helper and tested with both a single-entry and a multi-entry header. Which entry is the real client depends on what Render puts in front of gunicorn, so a deploy check compares the stored hashes from two networks (task 7.3). Replies don't wait for the mail service: the email is sent after the response is returned, so a known and an unknown address take the same time. The signup form has a hidden field that people leave empty. Signing in cycles the session key, stores `subscriber_id` in the Django session with a 30-day limit and never calls Django's `login()`; every request loads the subscriber by id and treats a missing one as signed out, so deleting the account ends other browsers' sessions. Sign-out flushes the session. Pages with tokens or choices are `noindex`, `no-store` and `Referrer-Policy: no-referrer`. Every POST needs a CSRF token except the one-click unsubscribe post, where the signed address is the proof. Pages respond the same for unknown addresses, so they can't be used to check who has signed up. The weekly email links to the sign-in page, never to a page that signs in by itself.

### Signed links for confirmation and unsubscribe
Both use Django's `TimestampSigner`-style signing with the secret key and a salt per purpose. Confirmation expires after 7 days. Opening it shows a Confirm button and only the POST confirms, so a mail scanner can't confirm anyone, and it doesn't sign the visitor in; they use the code like anyone else. The unsubscribe link carries the subscriber id and never expires, because an old email must still work, and deleting the account makes old links do nothing. Opening it shows a button and the masked address; only the POST pauses. The same address accepts the one-click post from `List-Unsubscribe-Post`. Unsubscribing pauses rather than deletes, so resuming is one click; deleting the account is a separate, confirmed action.

### Choices are rows, so more emails can come later
`DigestChoice` rows belong to a `Subscriber` with a `kind`: `area` (the `GeoFilter` query string, e.g. `state=vermont` or a metro with `town=` pairs, "All of the Northeast" is stored as `all=1`, so an empty parse can be told from a stale one), `near` (label, latitude, longitude, miles), `town` (town, state) or `venue` (foreign key to `Venue`, deleted choices cascade away). Storing the area as the same query string the cookie and calendar feed use means `parse_geo_filter()` does the resolving. It drops unknown slugs, and an empty `GeoFilter` matches every event, so the digest calls an `area` choice stale unless the parsed `GeoFilter.query_string` equals the stored string (apart from `all=1`), and selects nothing for a stale one. This catches a partly vanished choice too, such as a dropped metro or a renamed town, which would otherwise parse to the whole state or metro and widen the email. Neighborhood narrowing from a remembered filter is dropped when the form starts from it (the choices form offers no neighborhoods), so a stored area string never holds `neighborhood=` pairs. Choices are validated on write and capped at 20 per subscriber. A future "several emails per subscriber" change would add a digest between subscriber and choices; this version keeps one implicit digest and does not build that.

A venue deleted from the database removes its choice by cascade. The "no longer listed" marker covers areas and towns that vanish (sheet sync never deletes venues, so a vanished venue is rare).

### Selection is a union built in one query
`core/digest.py` builds one `Q` per choice and ORs them, then filters `Event.objects` (approved only) to the window and `is_cancelled=False`. `Event.starttime` can be null; the range filter leaves such events out. Matching uses `event.venue`, as the calendar feed does, so an event with a `venue_override` can show a different venue than the one it matched on; that is accepted. Area choices use `GeoFilter.q(prefix="venue__")`; town choices use the case-insensitive town and state match `GeoFilter` uses; venue choices use `venue_id`. The distance choice cannot be a plain `Q` (haversine on `exact_location`, which is a property that falls back from place to sheet coordinates), so it picks the venue ids first: load located venues once per run (about 730), keep those within the miles with `location.miles()`, and use `Q(venue_id__in=ids)`. Loading venues once per run, not per subscriber, keeps the cost to one query plus Python arithmetic.

### Sending
A new `send_weekly_digests` command based on `RecordedCommand` loops over confirmed, unpaused subscribers whose `last_digest_week` is not this week. It claims each with a conditional update of `last_digest_week` (so overlapping runs can't both send), builds and sends the email, and puts the old value back if the send fails. A send that succeeds but whose later bookkeeping fails could repeat; that is accepted. Sends are paced under the account's rate; a throttling reply counts as a failed send. The "week" is the Monday on or before the send day, New York time. A manual rerun on a Sunday would pick the previous Monday's week; this is tested. A rerun the same week therefore does nothing for sent subscribers and retries failed ones. It also deletes unconfirmed subscribers older than 7 days and expired codes older than a day. Send order is by id, with `--limit` and `--dry-run`. Logs name no address (the subscriber id only).

The window is the send day through the seventh day after it, New York time. A new Render cron job, `newenglandmusic-digest`, runs `bin/digest.sh` weekly. The day and hour are an open question below; the default is Thursday 13:00 UTC (8 or 9 am eastern), so people can plan the weekend.

### Mail sender gains a raw-message path
`SesMailSender.send_email()` cannot add headers. A new `send_raw_email()` builds a `multipart/alternative` MIME message with Python's `email` package and sends it with SES `send_raw_email`. The existing method and its callers are unchanged (it swallows `ClientError`, so no digest code path calls it). The confirmation and sign-in views send after the response and catch the raised errors, logging them rather than returning a 500. All three emails use the new path so they share one code route and one failure behaviour. The sender uses `email.message.EmailMessage`, which refuses line breaks in headers. Failures raise, and the command catches both `ClientError` and boto's credential errors (`BotoCoreError`) per subscriber. Event text goes into HTML only escaped, and event links use the site's own `/event/<id>` address built from `SITE_URL`. The sender is refused when `DEFAULT_FROM_EMAIL` is still `webmaster@localhost`, and likewise when `SITE_URL` is blank, localhost or not `https://`: `SITE_URL` falls back to `RENDER_EXTERNAL_URL`, which Render sets only on the web service, so a cron job copying a blank value would email dead links. `SITE_URL` must be set on the web service before the job is enabled.

### Screens
New: `/digest` (signup), `/digest/check-email`, `/digest/confirm/<token>`, `/digest/sign-in`, `/digest/preferences`, `/digest/unsubscribe/<token>`, and the email templates. The footer gets a "Weekly email" link. The signup and preferences pages share one choices form; the area picker reuses the markup of the listing's area filter, the near-a-place field reuses the location form's suggestions, and towns and venues use a text search with suggestions. The footer link is added as a menu item, as the footer's other links are. Their look is left to the design step, hence the `needs-design` label. The town and venue suggestions list public venue names only and are limited like other suggestions.

## Risks / Trade-offs

- **Spam and abuse of the signup form** (someone enters another person's address). Double opt-in means the victim gets only confirmation emails, at most 3 an hour, and the per-client limit and hidden field slow a bot. This also lets a stranger use up someone's code allowance for an hour; that is accepted. A bot challenge is not included.
- **Bounces and complaints.** SES suspends accounts with high bounce or complaint rates. This version relies on SES's own suppression list and a check of the bounce rate before launch; an automatic feedback webhook is an open question.
- **Mail from the site's own domain** needs SPF, DKIM and DMARC aligned before launch, listed in `PRODUCTION.md`.
- **SES sandbox.** Until production access is granted, only verified addresses receive mail. This is a launch step in `PRODUCTION.md`, not code.
- **Deliverability.** A new sender sending a weekly list needs SPF, DKIM (SES provides) and low complaint rates; the one-click unsubscribe and plain pause help.
- **The distance choice reads venue coordinates**, some of which are town centres; the miles are approximate, as they are for the event listing's distance labels.
- **The site starts storing personal data** (email, and the looked-up ZIP or town's point). The privacy page changes, and delete-account really deletes (backups age out on their own schedule). Editors can see every address in the admin; the admin offers no export and no send action.

## Migration Plan

One migration creates the four tables; nothing existing changes. Roll out by deploying with the cron job suspended, sending a dry run, then verifying the sender in SES and enabling the job. Rollback is suspending the job; removing the tables later loses only subscribers.

## Testing and mocking

- **Amazon SES:** tests never call boto3. The sender takes an injectable client (as `SesMailSender(ses_client)` already does); tests replace the module's `aws_mail_sender` with one holding a fake client that records the raw messages it is given, and can be told to raise `ClientError`, a credentials error or a throttling reply. Tests read the recorded MIME for parts, links and headers.
- **Census Gazetteer / location lookup:** tests build small Gazetteer files with `core/tests/census_fixture.py` and load them, as the location tests do; nothing is downloaded.
- **Sheet, Google Places, OpenStreetMap, ticketing and music services:** not touched by this change. Tests create `Venue`, `GeoArea` and `Event` rows directly.
- **Time:** tests patch `django.utils.timezone.now` so weeks, the 7-day link expiry and the 15-minute code expiry are exact.
- The whole suite must pass with outbound network blocked.

## Open Questions

Pause, resume and delete-account were not asked for in the thread; they are a deliberate addition that follows from the privacy rules.

1. **Send day and time.** The default is Thursday morning eastern. Does the owner prefer another day, such as Monday for the week ahead?
2. **The old `EmailSubscriber` addresses.** They were collected under another project's form and never agreed to this email. This change never copies them into `Subscriber` and leaves the table in place. Should the table and its admin page be deleted?
3. **A show-count limit and an empty week.** The proposal sends nothing on an empty week and caps the email at 50 shows. Are those right?
4. **Union versus intersection.** Choices are combined as "any of these". Someone who ticks an area and a venue outside it would still get the venue. Is that what is wanted?
5. **Bot protection and limits.** The proposal uses a hidden field and per-address and per-client limits (3 emails an hour, 10 requests an hour). Is a challenge also wanted at launch? Are the limits right?
6. **Distance list.** Are 5, 10, 25, 50 and 100 miles the right options?
7. **Bounce and complaint handling.** Should bounces and complaints reach the site (an SES notification webhook marking subscribers suppressed), or is SES's own suppression list enough for the first version?
8. **Keeping old data.** Paused or long-unused subscribers are kept until they delete them. Should they be deleted after some time, with a warning email?
9. **Several limits are proposed defaults, not decisions:** confirmation links last 7 days, codes 15 minutes, sessions 30 days, at most 20 choices.
10. **Signing up again with an unconfirmed address** keeps the stored choices and sends a fresh confirmation. Is it better to replace the choices with the new ones?
11. **Double opt-in.** Signup needs a confirmation link and a Confirm button, which the thread didn't ask for; it protects people whose address is entered by someone else. Is it wanted?

## Sketches

Three options for the sign-up page, the preferences page and the email layout, laid out at 1440×900.

- **[Option A: Index cards](sketches/a.html).** Thesis: keep to the site's paper look, with a plain sign-up card, a ruled preferences card with four labelled rows (areas, near, towns, venues) shown as pills, and a text-first email grouped by day. Risk: four separate rows can feel like a settings form, and it gives no clue how many shows a choice brings in until it's saved.
- **[Option B: Sentence builder](sketches/b.html).** Thesis: choices read as one sentence ("Email me shows in Greater Boston, within 25 miles of 02139…"), so the any-of-these rule is obvious and sign-up is one short page. Risk: sentence slots are an unfamiliar control, harder to make accessible and to use on a phone, and the 20-choice limit may make the sentence long.
- **[Option C: Live preview](sketches/c.html).** Thesis: checkbox lists on the left and a preview of next week's email on the right, with match counts beside each choice, so people see what they'll get. Risk: it needs counts and a preview computed per request, and the two-pane layout must collapse to one column on phones.
