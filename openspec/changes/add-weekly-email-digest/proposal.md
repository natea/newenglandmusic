Issue: [#13 Visitors can signup to receive a weekly email of upcoming shows that match their interests](https://github.com/natea/newenglandmusic/issues/13)

## Why

Visitors can subscribe to a calendar feed of an area, but only if they use a calendar app, and the feed shows every show in the area. Many fans would rather get one email a week that lists the shows near them. The site has no accounts and sends no email to visitors, so this is a new kind of feature, and the thread behind issue 13 settled how it should work.

## What Changes

- **Sign up with an email address.** A new page, `/digest`, asks for an email address and for which shows the visitor wants. No password is asked for.
- **A quiet account.** Giving an email address creates a small subscriber record behind the scenes. It is not a Django login user, so it can never reach the admin.
- **Confirmed by a link.** The site sends a confirmation email, and the weekly email starts only after the visitor follows its link and presses a Confirm button. Unconfirmed sign-ups are deleted after 7 days.
- **Sign in with a code, no password.** To change preferences later, the visitor asks for a 6-digit code by email, types it in, and lands on a preferences page. The code works once and expires after 15 minutes.
- **Three ways to choose shows**, which can be combined (a show is included if any choice matches):
  - **Areas:** any region, state or metro area, as the listing and the calendar feed offer them, including a metro's chosen towns, or "all of the Northeast".
  - **Near a place:** within a chosen number of miles of a ZIP code or town, using the same lookup as the location form.
  - **Follow:** particular towns, or particular venues.
- **One weekly email.** A new scheduled command sends each confirmed subscriber one email a week, listing the upcoming week's matching shows by date, each linking to its event page. Nothing is sent when no show matches.
- **Easy to leave.** Every email carries a one-click unsubscribe link (also as the `List-Unsubscribe` headers), and the preferences page can pause the email or delete the account and everything stored with it.
- **Privacy page** is updated: the site now keeps an email address, the choices and, for a "near a place" choice, the place's rounded coordinates.
- **Not included:** genre choices (they need a genre selector, a separate proposal this one doesn't depend on), text messages and phone numbers, following bands, daily emails, and several emails per subscriber. The data model leaves room for several emails per subscriber later, without building them.

## Capabilities

### New Capabilities
- `email-digest-subscriptions`: signing up, confirming, signing in with a code, choosing and changing the shows wanted, pausing, unsubscribing and deleting the account.
- `weekly-digest-email`: which shows a subscriber's choices select, what the weekly email contains, and the scheduled command that sends it exactly once a week.

### Modified Capabilities
- `scheduled-jobs`: a third, weekly cron job for the digest.

The area choices reuse the region, state and metro rules that `event-geo-filter` defines, and the distance choice reuses `event-distance`'s lookup, without changing their requirements.

## Impact

- **New models and a migration:** `Subscriber`, `SignInCode`, `DigestChoice` and `MailRequest`, described in `design.md`. `MailRequest` is an address-and-time log that exists only for the sending limits. The existing `EmailSubscriber` table is never copied into the new one; `design.md` asks whether to delete it.
- **New code:** subscription views, URLs and templates (signup, check-your-email, preferences, unsubscribe); a digest module that turns choices into an events query; a `send_weekly_digests` command based on `RecordedCommand`; the footer link; the admin page for subscribers.
- **Email sending:** the existing Amazon SES sender sends plain messages without custom headers. It gains a raw-message path so the emails can carry `List-Unsubscribe` headers. The sender address must be verified in SES, and SES must be out of its sandbox before real subscribers can receive anything.
- **Scheduling and docs:** a new weekly cron job in `render.yaml`, `bin/digest.sh`, and notes in `PRODUCTION.md` and `.env.example`.
- **Needs design:** the signup page, the preferences page and the email layout are new screens, so the change is labelled `needs-design`.
- **Dependencies:** none new. `boto3` and Django's signing and sessions are already in use.
