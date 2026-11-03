Issue: [#11 Let's make an About page](https://github.com/natea/newenglandmusic/issues/11)

# Design

## Context

The privacy page (`/privacy`) is the model: a template in the repo, served by a `TemplateView` route in `core/urls.py`, linked from a hard-coded footer link in `base.html`, and covered by `core/tests/test_privacy_page.py`. Routes in `core/urls.py` come before the static-page catch-all in `nycnoise/urls.py`, so `/about` wins over any admin-made `StaticPage`. The footer also lists admin-managed `MenuItem`s. `CONTACT_EMAIL` (a setting, empty by default) is already given to every template as `contact_email` by a context processor, and the event form already uses it for a `mailto:` link. See proposal.md for why and what.

## Goals / Non-Goals

**Goals**
- A page that reads well with no JavaScript and no database content.
- Feature descriptions that link to real pages, so they can't point nowhere.

**Non-Goals**
- Storing or reviewing suggestions. That is `add-venue-suggestions`, still in flight and not yet built.

## Decisions

**1. A repo template, not a `StaticPage` row or a menu item.** The text is reviewed in the pull request, tested, and the same on every deploy. A `StaticPage` would need a manual step in the live admin and would be empty on a fresh database, so the footer link could 404. Alternative rejected: a `StaticPage` plus a `MenuItem`, which lets the owners edit the text without a deploy, but loses the tests and the guarantee that the link works. The privacy page made the same choice.

**2. The contact route is a `mailto:` link, not a form.** It needs no model, no spam protection and no review screen, and the invitation is open-ended ("any other ideas"), which a fixed form would not fit. The link's subject line is "Suggestion for New England Music" so suggestions are easy to spot (the site name comes from `site_name`). Alternative rejected: reusing the venue-suggestion form, which doesn't exist yet and covers venues only.

**3. The link is left out when `CONTACT_EMAIL` is empty.** `CONTACT_EMAIL` defaults to empty, and a `mailto:` with no address looks broken. The page then shows only the invitation text and the event form link.

**4. Feature list is plain HTML, written to match the pages that exist.** Links use `{% url %}` where a name exists (`saved_shows`, `act_index`, `submit_event`, `calendar_feed`) so a renamed route fails the tests instead of breaking the page. The list only names features in the shipped specs.

**5. The footer link is hard-coded beside Privacy,** as the privacy link is, so it shows on every page even with an empty menu table. The sitemap gets the address added to its list of fixed pages.

## Risks / Trade-offs

- **Suggestions arrive by email, unstructured** → fine for the expected volume; when `add-venue-suggestions` ships, the page can point venue suggestions at its form (a small follow-up edit).
- **The feature list can go stale** → the tests check its links resolve; wording is reviewed when features change.
- **Footer gets longer on small screens** → the design step checks it.

## Testing

No outside service is touched, so nothing needs mocking. The tests use Django's test client and `override_settings(CONTACT_EMAIL=...)` for the two email cases. The sitemap test reads the sitemap view's output.

## Open Questions

- **The text.** What Nate, Sooz and Mark each want said about themselves (roles, a line each, links to their own sites), and the motivation in the owners' own words. The proposal's implementation drafts neutral placeholder wording that the owners edit at review; the specs only require that the three names and a "why" section appear.
- **Which address receives suggestions.** The existing `CONTACT_EMAIL`, or a separate one for the About page? It doesn't change the tasks: the page reads `contact_email` either way.
- **Whether to link `/suggest-venue`** once `add-venue-suggestions` is built. It can be added then without changing these specs.

## Sketches

Three layouts for the About page, each in the 42em column on the grey ground. Open them in a browser.

- [Option A: Plain page](sketches/a.html): Match the privacy page: headings and prose on the grey ground, with the tour as a plain linked list. Cheapest and most consistent.
- [Option B: Index card](sketches/b.html): Put the page on the act card with a plum About tab, sections divided by plum rules and a label column, and the invitation as a lavender strip.
- [Option C: Invitation first](sketches/c.html): Lead with a lavender strip and two pill buttons for writing in or adding a show, then plum bars for Why, What it does and Who.
