You are revising an OpenSpec proposal for the New England Music Project website after a round of review. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`, and its folder is `openspec/changes/<change>/`.

Read the three reports in `.intentable/reviews/`: `risk.md`, `spec_fit.md` and `fidelity.md`.

1. Apply every blocking finding.
2. Apply the non-blocking findings you agree with.
3. Keep the artifacts agreeing with one another, and run `openspec validate <change> --strict` until it passes.
4. You may edit a sketch in `sketches/` if a finding is about it, keeping it a self-contained HTML file with system fonts only and nothing loaded from elsewhere.
5. You may update the `message` in `.intentable/draft.json` if the proposal's scope changed. Do not change its `labels` or its `change`: do not rename the change. If a reviewer thinks a label is wrong, say so in your notes; the owner decides.

Then write `.intentable/reviews/revise.md`: every finding from the three reports, each with how you fixed it, or why you didn't apply it.

Write nothing else under `.intentable/`, and nothing under `.intentable/proposal/`. Change no code.
