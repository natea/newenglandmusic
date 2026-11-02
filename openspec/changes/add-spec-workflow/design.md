## Context

`triage` and `clarify` (archived as `2026-11-02-add-triage-clarify`) leave an issue in `spec-review` with a summary. The intentable bridge starts runs over Fabro's API, in the `daytona` environment, targeting a commit of natea/newenglandmusic. It reads a run's `.intentable/result.json` from its artifacts, applies it, and deletes the run's sandboxes.

Nate's rules apply here too:
- runs read the code and push nothing;
- every run ends with its result;
- Claude Code runs on the Max subscription through ACP, and the vault's API key only satisfies Fabro's provider check;
- drafts are published before G2 on a `change/<name>` branch with "Draft" in the commit subject, so their Spek page builds (`AGENTS.md`, `spec-pages`).

The review loop is the `dev-review-proposal` skill from intentable: three fresh reviewers, one lens each, revising until all three are satisfied on one revision.

## Goals / Non-Goals

**Goals:**
- An issue in `spec-review` gets a complete OpenSpec change. Three reviewers either pass it or mark it as not passed, and no person's input is needed during the run.
- The draft reaches a `change/` branch, and so its Spek page, with no GitHub write access in the sandbox.

**Non-Goals:**
- Starting the run and committing the draft. Those are the bridge's job, in intentable's `add-spec-runs`.
- G2 through the issue, moves out of `spec-review`, revising a draft after Nate comments, and Sooz or Mark picking a sketch.

## Decisions

**The graph.**

```
start -> install -> propose -> check_draft -> route
route -> sketch -> check_sketches -> fork    (needs-design)
route -> fork                                (otherwise)
fork -> risk, spec_fit, fidelity -> merge -> check_reviews
check_reviews -> finish   [outcome=succeeded]   (all yes, or round limit reached)
check_reviews -> revise   (otherwise)
revise -> recheck -> fork  (recheck is the same draft check; the reviewers run again)
finish -> exit
```

- **Every agent step** (`propose`, `sketch`, the three reviewers, `revise`) is `backend="acp"` with `acp.command="claude-agent-acp"`, as in `triage`. Each one therefore runs Claude Code on the Max subscription. None is a Fabro prompt stage, which would call the provider API with the vault key.
- **`install`** pins Claude Code and the ACP adapter at the versions `triage` uses, and `@fission-ai/openspec` at 1.16.0, the version this repository's artifacts were written with. It also writes the names of every folder in `openspec/changes/` and `openspec/changes/archive/` to `.intentable/existing-changes.txt`. It writes them before the agent runs, because Fabro's local checkpoint commits make the checkout's `HEAD` an unreliable base. The checker strips an archive folder's `YYYY-MM-DD-` prefix before comparing.
- **`check_draft`** runs `bin/check-intentable-result spec --draft` on `.intentable/draft.json`. It applies the name rules, the bounds and `openspec validate --strict`, and writes nothing. If it fails, the run ends (`on_failure="exit"`), so an invalid draft is never shown to reviewers.
- **`check_reviews`** is `bin/check-intentable-reviews`:
  - it keeps the round number in `.intentable/reviews/round`;
  - it moves each round's reports and revise notes to `.intentable/reviews/<round>/`;
  - the revise notes written after round N are filed with round N's reports, the round they answer;
  - when the loop ends, it writes `.intentable/reviews/summary.md` and `.intentable/reviews/outcome`;
  - it exits 0 when the loop should end, and 1 when another round is needed.

  The edge into `revise` must therefore be the failure route, not the `on_failure="exit"` default. Task 1.1 checks this with `fabro validate` and a dry graph. If a conditional edge doesn't override `on_failure`, the script instead sets `context.review_done`, the edges branch on that, and the script always exits 0.
- **Reviewers run in one checkout**, since Fabro's fan-out shares it. Each writes only its own report file, so there is no race. Each is a separate agent node, and so a fresh session: it hasn't seen the propose agent's reasoning, only the files, which is the skill's rule that the author's conclusions stay out of the brief. From round 2, each prompt points at the previous round's `revise.md`, which is the skill's "told what changed since its read".
- **`finish`** runs `bin/check-intentable-result spec`:
  1. it checks the draft again;
  2. it empties `.intentable/proposal/` and copies the change folder's contents into it;
  3. it copies the summary to `.intentable/review.md`;
  4. only then does it write `.intentable/result.json`, with `reviewed` read from `.intentable/reviews/outcome`, and `files` as paths relative to the change folder (Fabro's globs match leading dots, so `.openspec.yaml` is collected).

  So `result.json`, `review.md` and the proposal files exist only in the `finish` stage's artifacts. No earlier step writes under those paths: the prompts say so, and Fabro records a path again only when its content changes, so an earlier identical copy would leave a file out of `finish`'s artifacts. The bridge would then refuse the draft loudly, as "a file missing". The bridge reads the proposal files from the same stage as the result, which avoids ambiguity between stage versions. Fabro numbers stages separately from retries.

**Sketches** (Nate's decision, 2 November 2026: "sketches should be included in the proposal if design is needed").
- After the first `check_draft`, a `route` script reads `.intentable/draft.json`. With `needs-design`, the graph goes to `sketch`; otherwise it goes straight to the fan-out. The edge mechanism is the one task 1.1 settles.
- `sketch` is an ACP agent with the Impeccable plugin, installed in `install` from its marketplace (`pbakaus/impeccable`) at a pinned version. It is told to run Impeccable's decision step unattended: three options, each a self-contained HTML mock with inline CSS and no scripts, at 1440×900. It is also told not to generate images, so every file stays text. It copies the mocks and the options' payload into the change's `sketches/`, and adds a "Sketches" section to `design.md` that links each one.
- It runs once. `check_sketches` checks the sketches at once, so a missing or unsafe one fails cheaply, before any reviewer. The reviewers then review the sketches with the rest of the change, and revise may edit a sketch but never regenerates the set. `recheck` checks their safety again.
- `route` records the labels in `.intentable/route.json`, and revise may not change them, so the sketches always match the `needs-design` label. A reviewer who thinks the label is wrong says so in the report, and that goes to Nate in the summary. Nate corrects a wrong label himself; the run doesn't.
- `sketch.md` says to use system fonts or inline styles only, so sketches show layout and colour but not the site's own typefaces (the policy below blocks font files too): no web fonts, no outside stylesheets or images. Three of the Impeccable mocks committed as context load Google Fonts, and the sketch agent would otherwise tend to copy them.
- **Safety.** Sketches are written by an agent from issue text and served from the fork's Pages domain, which natea's other Pages sites share. So there are two checks. The run's checker parses each sketch against an allowlist (decoded entities; static elements and inline styles only; URLs only `#…` or `data:image/`). `bin/publish-spek-page` also adds a Content-Security-Policy meta tag to every published sketch, and copies only regular files, never links, in case something reaches a `change/` branch without the checker. The tag goes at the very start of the file, after any doctype, so the browser applies it before anything else in the file. A policy in a meta tag can't stop a `meta` refresh redirect or framing by another site; the allowlist keeps both out of the run's sketches, and for anything else the worst left is a redirect away, not code running on the domain.
- Impeccable's design context is committed with this change, so the sandbox's checkout has it (Nate's decision, 2 November 2026: the `.impeccable` files are useful for making new sketches). That means `.impeccable/config.json`, `design.json`, `surfaces/` and `mocks/`. It also means `PRODUCT.md`, which Impeccable reads first (Nate confirmed, 2 November 2026). `DESIGN.md` is already committed. Task 1.4 checks that the JSON files parse, since another session is editing them. Left out are the per-machine and per-session files: `config.local.json` and `hook.cache.json` (already excluded locally), `questions/` (one session's question logs) and `review/` (screenshots, binary). These files come from another session's design work in the main checkout. They are committed as they stand when this change is applied, and that session keeps editing them.
- Picking one option is left to the later stage where Sooz or Mark choose. At G2 Nate sees all three.
- The sketches are published beside the Spek page (`spec-pages` delta), at `changes/<name>/sketches/a.html` and so on. This replaces the plan's separate assets branch for sketches, since Nate put them in the proposal itself.
- Nate's decision, 2 November 2026: a sketch is chosen before anything design-related is built, but G2 needn't wait for the pick. Later he may drop the choosing step and have the design built without waiting for confirmation. The picking stage carries this.

**Briefs.** Each reviewer prompt gives its lens, the change folder path, `openspec/specs/`, `AGENTS.md`, `openspec/config.yaml` and the report format.
- There is no project dictionary in this repo, so spec fit checks vocabulary against the existing specs.
- Fidelity has no memory file in the sandbox. Its decision record is:
  - the thread, for the requester's decisions;
  - `AGENTS.md`;
  - the archived changes' designs, where Nate's dated decisions are kept.
- The bridge posts as `natea` with its marker. Both `propose.md` and `fidelity.md` say such a comment is the bridge's, not Nate speaking, as the triage prompts do.

**Round limit: 5** (Nate's decision, 2 November 2026: first 3, then 5 after the review of this very proposal took five rounds; the skill itself sets no limit). At the limit the run doesn't stop empty-handed: it ends with the draft marked not passed and the open findings in the summary.
- The limit caps cost.
- A run that hits it still ends with its draft, since a draft with open findings is more use to Nate than a failed run.
- `review.md`'s first line and `reviewed: not-passed` both say it wasn't passed.

**The result.**
- `labels` may carry `needs-design`, the one later-stage label this stage knows about. The plan says `needs-design` routes the issue to Impeccable.
- `state` is always none. The issue leaves `spec-review` only at G2, which a later change builds.
- `reviewed` gives the bridge the review's outcome as data, so it doesn't have to read words out of `review.md`. `files` lets it check that it received every file.
- The 90-file cap leaves room under Fabro's 100-file collection limit for the result and the summary. Path segments Fabro prunes (`target`, `dist` and the like) and non-text files are refused, because they would silently go missing or be mangled on the way to the branch.

**Name rule.** The name must match `^[a-z0-9]+(-[a-z0-9]+)*$`, at most 60 characters. That is stricter than `bin/publish-spek-page`, which accepts any name its page path can hold, so every accepted name gets a page. The checker passes the name to `openspec` only as a separate argument, never through a shell.

**Testing.** No external service is called in tests:
- the configuration tests read the workflow files;
- the checkers run as subprocesses on temporary folders holding fixture changes and reports;
- `openspec` is replaced by a fake executable placed first on `PATH`. It exits with a chosen status and prints a chosen summary line, so the suite runs offline and where `openspec` isn't installed (CI);
- Fabro, Claude, GitHub and Impeccable aren't touched (Impeccable's install and the sketch agent are covered by the configuration tests and the live check);
- the live check is a manual task.

## Risks / Trade-offs

- **[Usage]** A run takes up to 21 agent sessions on the Max subscription (1 propose, 15 review, 5 revise), or 22 with sketches. → The round limit, and the bridge starts one `spec` run per issue.
- **[Time]** Up to twelve sequential agent phases, which may not fit the bridge's three-hour sandbox lifetime. → The live check records how long a round takes. If five rounds don't fit, Nate decides whether to raise `SANDBOX_LIFETIME_MINUTES` or lower the limit. If the lifetime runs out, the run fails and is reported.
- **[A reviewer is never satisfied]** → The limit ends the loop with the draft and its findings for Nate.
- **[The agent edits code]** The prompt forbids it, and only `.intentable/proposal/`, which holds just the change folder, leaves the sandbox.
- **[Issue text steering the agent]** As with `triage`:
  - inputs never reach a command;
  - git access is read-only;
  - the result is checked before the bridge uses it.
- **[A name already used by an unmerged branch]** The agent can't see branch names, so the bridge finds the clash only after the run. → Accepted as a known cost; the bridge reports it.

## Open Questions

- Should the agent be able to say an issue isn't ready for a proposal after all, sending it back to `needs-info` with a question? This change leaves that out. Once in `spec-review`, the agent writes the best proposal it can and records the gaps as open questions.
