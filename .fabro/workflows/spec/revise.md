You are revising an OpenSpec proposal for the New England Music Project website after a round of review. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`, and its folder is `openspec/changes/<change>/`.

`.intentable/reviews/round` holds the number of the round just finished. Read that round's three reports in `.intentable/reviews/<round>/`: `risk.md`, `spec_fit.md` and `fidelity.md`.

1. Apply every blocking finding.
2. Apply the non-blocking findings you agree with.
3. Keep the artifacts agreeing with one another, and run `openspec validate <change> --strict` until it passes.
4. You may edit a sketch in `sketches/` if a finding is about it, keeping it a self-contained HTML file with system fonts only and nothing loaded from elsewhere: no scripts, event handlers, forms, iframes, SVG or HTML comments, no `<meta>` but `charset="utf-8"`, links that are `#` fragments only, and images only as `data:image/` URLs. A later step checks it, and the run fails if it breaks these rules. If the draft is a revision (`"revision": true`) left with one sketch, keep it at one: don't add sketches back. If it has `"scope": "sketches"`, change nothing but the sketches and the design's "Sketches" section. Leave files in `sketches/` whose names start with `round-` as they are.
5. You may update the `message` in `.intentable/draft.json` if the proposal's scope changed, keeping it to two to four plain sentences for a non-developer, with no file or spec names and no @-mentions. Do not change its `labels` or its `change`: do not rename the change. If a reviewer thinks a label is wrong, say so in your notes; the owner decides.

Then write `.intentable/reviews/revise.md`: every finding from the three reports, each with how you fixed it, or why you didn't apply it.

Write nothing else under `.intentable/`. Change no code.
