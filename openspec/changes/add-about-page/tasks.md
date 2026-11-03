# Tasks

## 1. The page

- [ ] 1.1 Add `core/templates/core/about.html` extending the base template, with the who, why, features and help-out sections and the contact link shown only when `contact_email` is set. Route `/about` in `core/urls.py` as a named route, ahead of the static-page catch-all. Draft neutral wording for the owners to edit. Verify: `core/tests/test_about_page.py` covers the "Page loads", "Page has its own title", "Features link to their pages", "Email link with a contact email" and "No contact email" scenarios.

## 2. Finding it

- [ ] 2.1 Add the About link to the footer in `base.html` beside Privacy. Verify: a test for the "Footer link" scenario over the home, saved shows, event submission and privacy pages. The existing privacy page tests still pass.
- [ ] 2.2 Add the page's address to the sitemap in `core/sitemap.py`. Verify: a test for the "Sitemap" scenario.

## 3. Release

- [ ] 3.1 Run the full suite with outbound network blocked, then open `/about` on the dev server (port 8001) and check each link, on a narrow and a wide window. Verify: every test passes and no link is dead.
- [ ] 3.2 Have the owners review the wording of the text. Verify: they've approved it, or their edits are in.
- [ ] 3.3 With the user's go-ahead, push to `main`. Verify: `/about` loads on the live site and the footer link shows.
