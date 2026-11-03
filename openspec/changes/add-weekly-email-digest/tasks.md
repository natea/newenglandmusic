Issue: [#13 Visitors can signup to receive a weekly email of upcoming shows that match their interests](https://github.com/natea/newenglandmusic/issues/13)

## 1. Models and migration

- [ ] 1.1 Add `Subscriber`, `SignInCode` and `DigestChoice` (kinds `area`, `near`, `town`, `venue`) to `core/models.py`, with a migration. Venue choices cascade on venue deletion; emails are stored lowercase and unique.
- [ ] 1.1a Add `MailRequest` (address, client hash, kind, time), used by the sending limits, to the same migration.
- [ ] 1.2 Register `Subscriber` in the admin (address, confirmed, paused, created; deletable; choices shown inline).
- [ ] 1.3 Add `core/tests/test_digest_models.py` covering lowercase uniqueness, cascades on venue and subscriber deletion, and the admin list columns.

## 2. Mail sender

- [ ] 2.1 Add `send_raw_email()` to `core/utils_aws.py`: a text and HTML `multipart/alternative` message with optional extra headers, sent with SES `send_raw_email`, leaving `send_email()` unchanged.
- [ ] 2.2 Add `core/tests/test_mail_sender.py` with a fake SES client: both parts and the headers appear in the recorded message, a client error, a credentials error and a throttling reply are raised to the caller, a line break in an address is refused, and `send_email()` still behaves as before.

## 3. Signed links and sign-in codes

- [ ] 3.1 Add `core/digest_tokens.py`: purpose-salted signed tokens for confirmation (7 days) and unsubscribe (no expiry), and the sign-in code helpers (generate with `secrets`, keyed hash, constant-time check, 15 minutes, single use, newer code cancels older, 5 tries per code and 10 an hour per address, the 3-an-hour address limit and the 10-an-hour client limit).
- [ ] 3.2 Add `core/tests/test_digest_tokens.py` covering the scenarios for valid and altered links, the expired and used code, the lockouts, the address and client limits, and that the reply doesn't wait for the mail service (the fake sender is only called after the response is returned).

## 4. Choosing shows

- [ ] 4.1 Add `core/digest.py`: `events_for(subscriber, window)` as a union of area, near, town and venue choices over approved, uncancelled events, plus a helper that loads located venues once for the distance choices. A choice is stale unless the parsed `GeoFilter.query_string` equals the stored string (apart from `all=1`). Verify with 4.2.
- [ ] 4.2 Add `core/tests/test_digest_selection.py` covering every scenario in "Choices select shows": area, distance (6 and 14 miles), followed town and venue, union with no duplicates, unapproved events, a venue with no coordinates, an area choice that went stale selecting nothing, a partly vanished one (a dropped metro, a renamed town) selecting nothing, a null start time, "All of the Northeast", a metro narrowed to towns, and a remembered neighborhood narrowing stripped from the form (with 5.3).

## 5. Signup, confirmation and sign-in views

- [ ] 5.1 Add the choices form (areas and metro towns, near-a-place with the Gazetteer lookup and its candidate list, followed towns and venues) and the `/digest` signup view with the same response for known and unknown addresses, starting from the remembered filter and location.
- [ ] 5.2 Add the confirmation view (a button, no sign-in), the sign-in view (request and enter code) and sign-out, using the session (fresh key, 30-day limit, subscriber re-checked each request, no Django login).
- [ ] 5.3 Add `core/tests/test_digest_signup.py` and `core/tests/test_digest_sign_in.py` covering each scenario of the requirements on signing up again before confirming, signing up revealing nothing about other addresses, limits on emails to one address or from one client, and "Signing up needs only an email address", "Confirmation switches the email on", "Choosing which shows" (including the shared-town list and the rounded coordinates) and "Signing in with an emailed code", with the fake SES client and a small Gazetteer fixture. Include the link-then-button and scanner scenarios, the hidden field, CSRF on POSTs, the 20-choice limit, unknown places, and a line break in an address.

## 6. Preferences, unsubscribe and privacy

- [ ] 6.1 Add the preferences view (change choices, pause and resume, delete account with confirmation), the unsubscribe page and one-click post endpoint, the footer menu item, the `noindex` and `no-store` headers, and the privacy page text (including the sentence saying nothing is stored about visitors).
- [ ] 6.2 Add `core/tests/test_digest_preferences.py` covering every scenario of "Managing a subscription", "One-click unsubscribe" and "Privacy page and admin", including the "Area no longer listed" and "Area partly gone" marks on the preferences page, the sessions-and-pages-guarded requirement, that opening the unsubscribe link alone changes nothing, the one-click post without a CSRF token, an altered link, sign-out, a deleted subscriber's session, and resume.

## 7. The weekly email and its command

- [ ] 7.1 Add the email templates (text and HTML) and the builder in `core/digest.py`: grouping by date, the 50-show limit with the see-all link, cancelled shows left out, the unsubscribe and sign-in links.
- [ ] 7.2 Add `send_weekly_digests` based on `RecordedCommand`, with `--dry-run` and `--limit`, the once-per-week rule, per-subscriber failure handling, and the clean-up of old unconfirmed subscribers and codes. Set `self.job_summary`.
- [ ] 7.3 Add `bin/digest.sh`, the `newenglandmusic-digest` cron job in `render.yaml`, with `bin/digest.sh` sourcing `steps.sh`, the settings it needs (database, site address, sender, secret key, mail credentials, and `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION`, which settings read without a default), with the AWS keys and sender declared on the web service entry as `sync: false` so the job can copy them, and notes in `PRODUCTION.md` and `.env.example`: verified sender, leaving the SES sandbox, SPF, DKIM and DMARC, and checking the bounce rate; `SITE_URL` set on the web service before the job is enabled; and a deploy check that signs up from two networks and compares the stored client hashes.
- [ ] 7.4 Add `core/tests/test_weekly_digest_email.py` and `core/tests/test_send_weekly_digests.py` covering every scenario of "What the weekly email holds", "Sending once a week" and "Mail carries the headers readers expect": the window, cancelled shows, the 50-show limit (60 shows selected), text and HTML parts, one email per week on a rerun, paused and unconfirmed subscribers, a failed send, the dry run, the claim against overlapping runs, the unsubscribe headers, the missing mail service, sender and site address (blank or localhost `SITE_URL`), the client-address helper with single and multiple `X-Forwarded-For` entries, a throttling reply, `--limit`, event text escaped in the HTML part with a fixed subject ("Markup in a title"), the confirmation and code emails' raw path, a manual Sunday rerun, a deleted venue, and the cleanup of old unconfirmed sign-ups.
- [ ] 7.5 Extend `core/tests/test_scheduled_jobs.py` for the digest job: its schedule, start command, exact key set, no migrate step, and `bin/digest.sh` in the executable-scripts list and in the hard-coded `daily.sh`/`weekly.sh` loops of the unbuffered-output and real-commands tests.

## 8. Check the whole

- [ ] 8.1 Run `venv/bin/python manage.py test` with the network blocked and confirm every spec scenario has a passing test.
- [ ] 8.2 Run `openspec validate add-weekly-email-digest --strict`.
