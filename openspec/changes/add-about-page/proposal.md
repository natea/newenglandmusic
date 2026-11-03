# Proposal

## Why

The site has no page saying who makes it or why. A visitor can browse venues, shows and acts, but can't learn that Nate, Sooz and Mark are behind it, what it is for, or how to help. It also gives people no obvious way to say "you're missing this venue" or "here's an idea". An About page answers all three, and turns readers into contributors. See issue 11.

## What Changes

- **A public About page** at `/about`, written as a template in the repo, like the privacy page. It has four parts:
  - **Who:** an introduction to Nate, Sooz and Mark.
  - **Why:** the motivation for building the site.
  - **What it does:** a short tour of the features that exist today: the venue and show listings, the map, saved shows, searching venues and acts, band and artist pages, music previews (Spotify, Apple Music and YouTube play buttons), distance from a place the visitor names, and calendar feeds. Each links to the page where the feature lives.
  - **Help out:** an invitation to suggest missing venues, bands or artists, or to share any other idea.
- **How people send suggestions:** a "write to us" link using the site's contact email, with the subject line suggesting what it's about. The page also links to the existing event submission form for people who want to add a show. If no contact email is configured, the page still loads and shows the invitation without the email link.
- **A footer link** to the page on every page, beside the Privacy link.
- **The sitemap** lists the page.
- **Not in this change:** a suggestion form or any new place to store suggestions (the separate `add-venue-suggestions` change covers suggesting venues); accounts; editing the page's text from the admin; photos of the team.

## Capabilities

### New Capabilities

- `about-page`: the public About page, what it says, where it is linked from, and how visitors can contact the team.

### Modified Capabilities

None. No existing spec describes the footer or the sitemap's page list.

## Impact

- **Views and templates:** a new `about.html` extending the base template, and a route for `/about` in `core/urls.py`, which comes before the static-page catch-all. The footer in `base.html` gains the link.
- **Sitemap:** `core/sitemap.py` adds the page's address.
- **Settings:** reads the existing `CONTACT_EMAIL`, through the existing context processor. Nothing new to configure.
- **No models, no migrations, no management commands, no outside services.**
- **Screens:** one new page, so the change is labelled `needs-design`.
