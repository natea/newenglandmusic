# issue-proposals Specification

## Purpose
The `spec` workflow the intentable bridge starts for an issue in `spec-review`: an agent writes the issue up as an OpenSpec proposal, with sketches when it needs screens, three fresh reviewers check it for risk, spec fit and fidelity, and the reviewed draft and a summary go to Nate for his confirmation (G2). An issue that isn't ready goes back with a question instead.

## Requirements

### Requirement: A spec workflow exists

The repo SHALL have a `spec` workflow in `.fabro/workflows/spec/`. It SHALL install Claude Code, its ACP adapter and the `openspec` CLI at pinned versions. Then, in order, it SHALL run:
- an agent that writes the proposal;
- a step that checks the draft;
- a sketch agent, only when a new proposal needs screens, never for a revision;
- three reviewer agents in parallel;
- a step that reads their reports;
- a revise agent, after which the draft is checked and reviewed again;
- a final step that writes the result.

Every check step runs the default branch's copy of its script (see "A revision runs the default branch's checks").

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it installs pinned versions of Claude Code, the ACP adapter and `openspec`. In order, it has:
  - a `propose` agent using `propose.md`;
  - the draft check;
  - the `route` step, which sends a `needs-info` draft straight to the last step, and a revision straight to the fan-out;
  - the `sketch` agent and the `check_sketches` step on the `needs-design` route;
  - a fan-out to the agents `risk`, `spec_fit` and `fidelity`, each using its own prompt;
  - a merge;
  - the review check;
  - a `revise` agent using `revise.md`, which leads back through the draft check to the fan-out;
  - a last step running the default branch's copy, `.intentable/main/check-intentable-result spec`.

#### Scenario: A revision skips the sketch step

- **WHEN** the configuration tests read the graph
- **THEN** the `route` step's unconditional edge reaches the fan-out, and the `sketch` agent is reached only on the `needs-design` route, which the route step never prints for a revision

### Requirement: Every agent runs through ACP

Every agent step of the `spec` workflow SHALL be Claude Code through ACP (`backend="acp"`), so it runs on the Max subscription like `triage` and `clarify`.

#### Scenario: Every agent through ACP

- **WHEN** the configuration tests read every agent step of the graph
- **THEN** each has `backend="acp"` and the `claude-agent-acp` command, and no step is a prompt stage that calls a model directly

### Requirement: A proposal that needs screens includes sketches

When a new draft is labelled `needs-design`, a `sketch` agent with the Impeccable skill (pinned) SHALL run once, before the first review, and write three options to `openspec/changes/<change>/sketches/`: `a.html`, `b.html`, `c.html`, and `options.json`, a list with each option's `file`, `label`, `thesis` and `risk`. `design.md` SHALL link each sketch. Otherwise the step SHALL be skipped (Nate's decision, 2 November 2026). One sketch is allowed only for a revision: a revision that narrows to a picked option SHALL keep exactly that one sketch, with its `options.json` entry and its link in `design.md` (Nate's decision, 11 November 2026).

#### Scenario: Sketch step only for needs-design

- **WHEN** the configuration tests read the graph
- **THEN** a `sketch` agent using `sketch.md` is reached from the first draft check only on the route for `needs-design`, leads to the fan-out, and is not on the revise loop

#### Scenario: Sketches required with needs-design

- **WHEN** the draft has the label `needs-design` and `openspec/changes/add-venue-hours/sketches/` lacks `c.html` or `options.json`, or `design.md` doesn't link `sketches/a.html`
- **THEN** `bin/check-intentable-result spec --sketches` exits with a failure naming what is missing

#### Scenario: Options for each sketch

- **WHEN** `options.json` isn't a JSON list, has no entry for `c.html`, or has an empty thesis or risk
- **THEN** `--sketches` exits with a failure naming what is missing, since the issue comment shows them (Nate's decision, 3 November 2026)

#### Scenario: One sketch after a pick

- **WHEN** a revision draft with the label `needs-design` has only `sketches/c.html`, `options.json` with an entry for `c.html`, and `design.md` linking it
- **THEN** the last step's check accepts it

#### Scenario: Two sketches

- **WHEN** a revision draft with `needs-design` has `sketches/a.html` and `sketches/c.html` only, or a new draft has only `sketches/c.html`
- **THEN** the last step exits with a failure saying a new draft has three options and a narrowed revision one

### Requirement: Sketches are checked as soon as they are made

A `check_sketches` step SHALL run right after `sketch`, before the fan-out, running `.intentable/main/check-intentable-result spec --sketches`: the sketches are present, linked from `design.md`, and safe to publish. The draft check after revise SHALL check the safety of any sketches again, and the last step SHALL repeat the full `--sketches` check when the recorded labels include `needs-design`. For a new draft, the first draft check, before `sketch`, SHALL NOT require sketches.

#### Scenario: Unsafe sketch caught before review

- **WHEN** the sketch agent writes a `b.html` that loads a stylesheet from another address
- **THEN** `check_sketches` fails the run before any reviewer starts

#### Scenario: A sketch lost in revise

- **WHEN** revise deletes `sketches/c.html` from a `needs-design` change
- **THEN** the last step exits with a failure naming the missing sketch

#### Scenario: First draft check without sketches

- **WHEN** `--draft` runs on a new `needs-design` draft that has no `sketches/` yet
- **THEN** it accepts the draft

### Requirement: Sketches are safe to publish

`bin/check-intentable-result` SHALL parse each sketch as HTML, entities decoded, and accept it only if every element and attribute is on an allowlist of static HTML and inline styling, and every URL, in attributes or CSS, is a fragment (`#…`) or a `data:image/` URL. It SHALL refuse what browsers and its own parser could read differently: comments, SVG, declarations but the doctype, and markup inside `<style>`. Otherwise it SHALL fail, naming the file and the problem.

#### Scenario: A sketch browsers read differently

- **WHEN** a sketch has `<!-->` or `<!---` hiding a tag, any comment, `<svg><style>` or `<svg><title>` holding a tag, `<style/>`, a `<meta>` but `charset="utf-8"` or viewport, `image-set(` or `url(` to an address anywhere
- **THEN** the checker exits with a failure naming the file

#### Scenario: A sketch with a script

- **WHEN** `sketches/b.html` contains `<script>`, `onclick=` or an entity-encoded `jav&#x61;script:` link
- **THEN** the checker exits with a failure naming `sketches/b.html`

#### Scenario: A sketch that calls out

- **WHEN** a sketch loads `https://fonts.googleapis.com/css2?family=Open+Sans`, `//cdn.example/x.css`, or has `<form action="https://example.org">` or `<iframe srcdoc=…>`
- **THEN** the checker exits with a failure naming the file

#### Scenario: A safe sketch

- **WHEN** a sketch uses only inline `<style>`, system fonts, headings, lists, tables and `data:image/png` images
- **THEN** the checker accepts it

### Requirement: The draft's labels are fixed before review

The `route` step SHALL record the draft's labels and change in `.intentable/route.json`. The revise agent SHALL NOT change the labels, and every later check SHALL fail the run when `.intentable/draft.json`'s labels or change differ from the recorded ones.

#### Scenario: Revise renames the change

- **WHEN** route recorded `add-venue-hours` and, after revise, the draft names `add-venue-times`
- **THEN** the recheck exits with a failure saying the change was renamed

#### Scenario: Revise adds needs-design

- **WHEN** route recorded no labels and, after revise, the draft's labels are `needs-design`
- **THEN** the recheck exits with a failure saying the labels changed after routing

### Requirement: The spec workflow follows the workflow contract

The `spec` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author`, `issue_thread`, `change_name`, `feedback` and `revision_scope`, each with an empty default, and its propose prompt SHALL use all eight. No command step SHALL contain an input. The graph SHALL set `on_failure="exit"`, have no human gate, use no child workflow, and every `@` file reference SHALL be inside its own folder.

#### Scenario: Inputs used, commands without inputs

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it declares the eight inputs, `propose.md` refers to every one, and no command step contains `{{ inputs.`

#### Scenario: No gate, no children, references inside

- **WHEN** the configuration tests read the graph
- **THEN** it sets `on_failure="exit"`, has no human gate, names no child workflow, and each `@` reference names a file in `.fabro/workflows/spec/`

### Requirement: The spec workflow pushes nothing

The `spec` workflow SHALL NOT push a run branch or open a pull request, and SHALL ask Fabro for no GitHub permissions. The finished change SHALL leave the sandbox only through Fabro's record of the files the run changed, and the result and summary as run artifacts.

#### Scenario: Nothing pushed

- **WHEN** the configuration tests read the workflow's settings
- **THEN** it disables pull requests and run-branch pushing, declares no GitHub integration permissions, and collects exactly `.intentable/result.json` and `.intentable/review.md`

### Requirement: Reviewers are fresh, one lens each

Each reviewer SHALL be its own agent step with its own prompt and one lens: risk, spec fit or fidelity. Each prompt SHALL word its lens as the `dev-review-proposal` skill does. Spec fit's design rules SHALL be `openspec/config.yaml` and `AGENTS.md`. Fidelity SHALL treat a decision taken without the requester or the owner, and left unflagged, as blocking.

#### Scenario: Three lenses

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names one of the lenses risk, spec fit and fidelity, and no two name the same. The risk prompt asks for readers the task list misses. The spec fit prompt names `openspec/config.yaml` and `AGENTS.md` as the design rules. The fidelity prompt says an unflagged decision is blocking.

### Requirement: The fidelity reviewer reads the decision record

The fidelity prompt SHALL give as the decision record the issue thread, `AGENTS.md`, and the designs of the archived changes in `openspec/changes/archive/`. For a revision, the fidelity prompt SHALL also say to check each point of the feedback in the change's files, and each question in the message, and to treat a point not acted on, or a question not answered, as blocking, unless the message gives the reason. The fidelity prompt and the propose prompt SHALL both say that a comment ending with `<!-- intentable-bridge -->` is the bridge's, not the owner speaking.

#### Scenario: Decision record and bridge comments

- **WHEN** the configuration tests read `fidelity.md` and `propose.md`
- **THEN** `fidelity.md` names the thread, `AGENTS.md` and `openspec/changes/archive/`, and both say a comment ending with the bridge marker isn't the owner speaking

#### Scenario: Fidelity checks each point of the feedback

- **WHEN** the configuration tests read `fidelity.md`
- **THEN** it says that for a revision each point is checked in the files and each question in the message, and that one left without a reason is blocking

### Requirement: Reviewers write reports and edit nothing

Each reviewer SHALL write its report to `.intentable/reviews/<lens>.md` in the `dev-review-proposal` format: `SATISFIED: yes` or `SATISFIED: no`, then `BLOCKING:`, `NON-BLOCKING:` and `CONFIRMED OK:`, with `none` under an empty heading. It SHALL be told to change no other file. From the second round on, it SHALL be given the revise notes of the round before, as what changed since the last read.

#### Scenario: Reviewer prompts

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names its own report file, gives the four headings and the `none` rule, tells the reviewer to edit nothing else, and refers to the previous round's revise notes

### Requirement: Revise records what it did

The revise agent SHALL apply every blocking finding, and the non-blocking ones it agrees with. It SHALL write `.intentable/reviews/revise.md` listing each finding with how it was fixed, or why it wasn't applied. It SHALL NOT rename the change.

#### Scenario: Revise prompt

- **WHEN** the configuration tests read `revise.md`
- **THEN** it says to apply every blocking finding, to write each finding with its fix or reason to `.intentable/reviews/revise.md`, and not to rename the change

### Requirement: The review loop ends

`bin/check-intentable-reviews` SHALL keep each round's three reports under `.intentable/reviews/<round>/`, and the revise notes written after round N under `.intentable/reviews/<N>/` with that round's reports. It SHALL end the loop when all three reports start `SATISFIED: yes`. It SHALL send the draft to revise when any says no, unless five rounds have run. After the fifth round it SHALL end the loop with the review not passed. A missing or unreadable report SHALL count as not satisfied.

#### Scenario: All satisfied

- **WHEN** the three reports of round 1 each start `SATISFIED: yes`
- **THEN** the check ends the loop with the review passed after 1 round

#### Scenario: One not satisfied

- **WHEN** the risk report of round 1 starts `SATISFIED: no` and the others say yes
- **THEN** the check sends the draft to revise

#### Scenario: The round limit

- **WHEN** a report of round 5 still says no
- **THEN** the check ends the loop with the review not passed after 5 rounds

#### Scenario: Missing report

- **WHEN** the fidelity report is missing
- **THEN** the check counts it as not satisfied

### Requirement: The review is summed up for Nate

When the loop ends, `bin/check-intentable-reviews` SHALL write `.intentable/reviews/outcome`, `passed` or `not-passed`, and the review summary, `.intentable/reviews/summary.md`. The summary's first line SHALL be exactly `Passed by the reviewers after <n> round(s).` or `Not passed by the reviewers after <n> rounds.`, followed by every round's blocking findings, the revise notes filed with them, and the last round's non-blocking findings, which no revise answers.

#### Scenario: Summary written

- **WHEN** a run's review ends after 2 rounds with all three satisfied
- **THEN** `.intentable/reviews/summary.md` starts with the line `Passed by the reviewers after 2 round(s).` and holds round 1's blocking findings and the revise notes filed with them, and `.intentable/reviews/outcome` is `passed`

#### Scenario: Last round's other findings in the summary

- **WHEN** a report of the last round lists a non-blocking finding
- **THEN** the summary holds it

#### Scenario: A fenced report

- **WHEN** a report is wrapped in a code fence and starts `SATISFIED: yes`
- **THEN** it counts as satisfied

#### Scenario: Summary of a review not passed

- **WHEN** the review ends at the round limit
- **THEN** `.intentable/reviews/summary.md` starts with the line `Not passed by the reviewers after 5 rounds.`, and `.intentable/reviews/outcome` is `not-passed`

### Requirement: The summary is collected with the result

For a draft with a change, the last step SHALL copy `.intentable/reviews/summary.md` to `.intentable/review.md`, so it is collected in the same stage as the result.

#### Scenario: Summary beside the result

- **WHEN** the last step accepts a draft
- **THEN** `.intentable/review.md` is the same text as `.intentable/reviews/summary.md`, and no earlier step wrote `.intentable/review.md`

### Requirement: An issue that isn't ready goes back with a question

When the propose agent finds the issue isn't clear enough to write up, it SHALL write no change and set `.intentable/draft.json` to the state `needs-info`, exactly one `clarity:` label from 1 to 3, and a message that asks exactly one question (Nate's decision, 2 November 2026). The `route` step SHALL then send the run straight to the last step, with no sketch and no review. The last step SHALL write a result with that state, label and message, and no `change`, `reviewed` or `files`.

#### Scenario: Not ready

- **WHEN** the propose agent's draft has the state `needs-info`, the label `clarity:3` and one question
- **THEN** no reviewer or sketch step runs, and the result has the state `needs-info`, `clarity:3`, that question, and no change

#### Scenario: A send-back that breaks the rules

- **WHEN** a `needs-info` draft has `clarity:4`, two questions, names a change, or leaves a new folder in `openspec/changes/`
- **THEN** the checker exits with a failure naming the problem

### Requirement: The draft is named in its own file

The propose agent SHALL name the change and give its message in `.intentable/draft.json`, as `change`, `labels` and `message`. The revise agent may change the message, but not the labels or the change name. No step before the last SHALL write `.intentable/result.json` or `.intentable/review.md`.

#### Scenario: Draft check reads the draft file

- **WHEN** `bin/check-intentable-result spec --draft` runs with `.intentable/draft.json` naming a valid new change
- **THEN** it accepts the draft and doesn't write `.intentable/result.json`

### Requirement: The spec result names the change

The last step, the checker's `spec` mode, SHALL write `.intentable/result.json` from `.intentable/draft.json` and `.intentable/reviews/outcome`. For a draft with a change, it SHALL hold `change`, the change's name; `labels`, none or only `needs-design`; `state`, none; `message`, plain text for the person who asked; `reviewed`, `passed` or `not-passed`; and `files`, every file of the change, relative to its folder, dotfiles such as `.openspec.yaml` included. For a revision it SHALL also hold `revision: true`.

#### Scenario: A good result

- **WHEN** the draft names `add-venue-hours`, which validates and is new, with no labels and a two-sentence message, and the review passed
- **THEN** the checker writes a result with that change, no state, the message, `reviewed: passed` and `files` such as `[".openspec.yaml", "design.md", "proposal.md", "specs/venues/spec.md", "tasks.md"]`

#### Scenario: A revision's result

- **WHEN** the draft is a revision of `add-band-discovery-swipe` and the review passed
- **THEN** the result holds that change, `revision: true`, `reviewed: passed` and the folder's files after the revision

### Requirement: The change name is plain and new

`bin/check-intentable-result spec`, with or without `--draft`, SHALL fail the run, naming the problem, when:
- `change` isn't a kebab-case name of lowercase letters, digits and single hyphens, at most 60 characters;
- the change folder is missing;
- the change existed before the run in `openspec/changes/`, or in its archive with any `YYYY-MM-DD-` prefix removed, unless the draft is a revision;
- the draft is a revision, and its change didn't exist in `openspec/changes/` before the run, or another change folder is new.

#### Scenario: A name that isn't plain

- **WHEN** the draft's `change` is `../add-x` or `Add Venue Hours`
- **THEN** the checker exits with a failure about the name

#### Scenario: A change that already existed

- **WHEN** the draft names `add-spek-pages`, archived as `2026-11-02-add-spek-pages`
- **THEN** the checker exits with a failure saying the change already exists

#### Scenario: No change folder

- **WHEN** the draft names `add-venue-hours` and `openspec/changes/add-venue-hours/` doesn't exist
- **THEN** the checker exits with a failure saying the folder is missing

#### Scenario: A revision of an existing change

- **WHEN** the draft is a revision of `add-band-discovery-swipe`, which existed before the run, and no other change folder is new
- **THEN** the checker accepts the name

#### Scenario: A revision that makes a new change

- **WHEN** the draft is a revision of `add-band-discovery-swipe`, and the agent also created `openspec/changes/add-swipe-deck/`
- **THEN** the checker exits with a failure naming `add-swipe-deck` as new

### Requirement: Spec drafts must be valid and collectable

`bin/check-intentable-result spec`, with or without `--draft`, SHALL also fail the run, naming the problem, when:
- the change doesn't pass `openspec validate <change> --strict`;
- the change has more than 90 files, or a file over 256 KiB or 20,000 lines, past which Fabro's record of the file is cut;
- the change has a file that isn't UTF-8 text;
- the change has a path segment that Fabro skips when collecting, such as `node_modules` or `dist`; `bin/check-intentable-result` lists them all.

#### Scenario: Too many files

- **WHEN** the named change holds 91 files
- **THEN** the checker exits with a failure giving the count and the cap

#### Scenario: A file Fabro wouldn't collect

- **WHEN** the change has `specs/dist/spec.md` or a binary image
- **THEN** the checker exits with a failure naming the file

#### Scenario: A file too large

- **WHEN** a change's file is over 256 KiB or 20,000 lines
- **THEN** the checker exits with a failure naming the file

#### Scenario: Invalid change

- **WHEN** `openspec validate` fails for the named change
- **THEN** the checker exits with a failure that includes the validator's summary line

### Requirement: Spec drafts give no state and follow the message rules

`bin/check-intentable-result spec`, with or without `--draft`, SHALL fail the run, naming the problem, when the draft has a `state` other than none or `needs-info`, a label other than `needs-design` for a draft with a change, or when its message is missing, mentions anyone, or is longer than the other workflows allow.

#### Scenario: A state or another label

- **WHEN** the draft gives the state `building` or the label `ai-shippable`
- **THEN** the checker exits with a failure naming it

#### Scenario: A message that mentions someone

- **WHEN** the draft's message mentions `@sooz`
- **THEN** the checker exits with a failure saying messages mention no one

### Requirement: The proposal prompt states the rules

`propose.md` SHALL tell the agent to write planning artifacts only, grounded in the site's code; to follow `openspec/config.yaml` and `AGENTS.md`; to choose a new change name; to keep host and network names out; to record unsettled decisions as open questions; to send the issue back with one question when it isn't clear enough; and to write the message in two to four plain sentences, with no @-mentions. These are the rules for a new draft. A revision follows them except that it keeps its change's name, never sends the issue back, and may use up to six sentences (see "A revision's message answers the feedback").

#### Scenario: The prompt gives the rules

- **WHEN** the configuration tests read `propose.md`
- **THEN** it says:
  - to write planning artifacts only;
  - to follow `openspec/config.yaml` and `AGENTS.md`;
  - to keep host and network names out;
  - to record unsettled decisions as open questions;
  - when to send the issue back with one question;
  - to write the message in two to four sentences without @-mentions;
  - to write `.intentable/draft.json`.

#### Scenario: The prompt gives a revision's exceptions

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section says to keep the change's name, not to send the issue back, and to use at most six sentences

### Requirement: The propose agent leaves reviewing to later steps

`propose.md` SHALL tell the agent not to review the draft itself, to start no subagents or background tasks, and to stop only once `.intentable/draft.json` is written. The graph's goal, which every agent sees, SHALL NOT ask for reviewers (issue #14's first spec run, 6 November 2026: the propose agent started its own reviewers from the goal's wording and its session ended while it waited for them, with no draft).

#### Scenario: The propose agent finishes its own work

- **WHEN** the configuration tests read `propose.md` and the `spec` graph
- **THEN** the prompt says not to review the draft, to start no subagents or background tasks, and to stop only once `.intentable/draft.json` is written, and the graph's goal doesn't say the proposal is reviewed by reviewers

### Requirement: A guide explains the spec workflow

`docs/FABRO.md` SHALL describe the `spec` workflow: when the bridge starts it, the review loop and its limit, what the run leaves, and that the bridge, not the run, pushes the draft.

#### Scenario: Guide

- **WHEN** the tests read `docs/FABRO.md`
- **THEN** it has a section on the `spec` workflow that says the bridge commits the draft from Fabro's record of the files the run changed, and names the three lenses and the five-round limit

### Requirement: A revision answers the feedback

When `feedback` isn't empty, the propose agent SHALL revise the change `change_name` instead of writing a new one, and SHALL write `.intentable/draft.json` with `revision: true`, that `change` and the draft's labels. It SHALL act on each point of the feedback, changing the specs and their scenarios where the feedback changes behaviour, and record what the feedback leaves undecided as an open question. A revision SHALL NOT send the issue back.

#### Scenario: The propose prompt has the revision section

- **WHEN** the configuration tests read `propose.md`
- **THEN** it contains `{{ inputs.feedback }}` and `{{ inputs.change_name }}`, and says to revise that change rather than write a new one, and to write `revision: true`

#### Scenario: A revision that asks a question back

- **WHEN** a revision draft has the state `needs-info`
- **THEN** `bin/check-intentable-result spec --draft` exits with a failure saying a revision can't send the issue back

### Requirement: A revision after G2 changes only the sketches

When `revision_scope` is `sketches`, the propose agent SHALL change only files under `sketches/` and the design's "Sketches" section, since Nate has confirmed the rest, and SHALL write `"scope": "sketches"` in the draft. Its message SHALL name each request that would need the proposal itself changed.

#### Scenario: The prompt limits a revision after G2

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section contains `{{ inputs.revision_scope }}` and says that with `sketches` only the sketches and the "Sketches" section change, and other requests are named in the message

### Requirement: The draft check enforces a sketch-only revision

The draft check SHALL fail a draft with `"scope": "sketches"` that changes anything but files under `sketches/` and the design's "Sketches" section, compared with the commit `install` recorded in `.intentable/base` before any agent ran, since Fabro's checkpoint commits move `HEAD`.

#### Scenario: A sketch-only revision that changes the spec

- **WHEN** a revision draft with `"scope": "sketches"` also changed `specs/band-discovery/spec.md`, and a checkpoint commit after the propose step holds that edit
- **THEN** the draft check exits with a failure naming that file

### Requirement: A revision's message answers the feedback

A revision's message SHALL say what changed, answer each question the feedback asks, and name any request outside the issue's scope as one to file as its own issue (Nate's decision, 11 November 2026). The checker refuses a mention or more than 2,000 characters, as for a new draft, and the prompt asks for at most six plain sentences.

#### Scenario: The prompt asks for answers

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section says to answer each question in the message and to name out-of-scope requests as their own issues

### Requirement: A pick with changes narrows to one sketch

When the feedback picks one of the sketches and asks for changes to it, the propose agent SHALL revise that sketch under its own letter, remove the others and their `options.json` entries, and keep `design.md`'s "Sketches" section to that one (Nate's decision, 11 November 2026: "narrow it down to one refined sketch rather than expanding to more variations"). The revise agent SHALL keep a narrowed revision at one sketch.

#### Scenario: Prompts keep one sketch

- **WHEN** the configuration tests read `propose.md` and `revise.md`
- **THEN** `propose.md` says a pick with changes keeps only that sketch, revised, and `revise.md` says not to add sketches back to a revision that has one

### Requirement: A revision runs the default branch's checks

The `install` step SHALL copy `bin/check-intentable-result`, `bin/check-intentable-reviews` and `.fabro/workflows/spec/sketch.md` from the default branch into `.intentable/main/`, and every check step SHALL run those copies. A revision's checkout is its draft branch, which can predate the current checks, as the build's checkout can (`issue-builds`). The propose prompt SHALL point a revision at `.intentable/main/sketch.md` for the sketch rules.

#### Scenario: A revision on a branch cut before this change

- **WHEN** a revision run's checkout is a draft branch whose `bin/check-intentable-result` has no revision rules
- **THEN** the draft check that runs is the default branch's, and it accepts the revision

#### Scenario: Check steps run the copies

- **WHEN** the configuration tests read the graph
- **THEN** `install` fetches the default branch and copies the three files into `.intentable/main/`, and every check step runs `python3 .intentable/main/check-intentable-…`

### Requirement: A revision's draft is checked like a new one

`bin/check-intentable-result spec --draft` SHALL check a revision with every rule a new draft has, except that its change existed before the run. For a revision labelled `needs-design` it SHALL also require the sketch set (three, or one), since a revision doesn't pass the `--sketches` step. The route step SHALL record the revision's labels and change, as for a new draft, and send it to review, so the sketch agent doesn't run.

#### Scenario: A revision goes straight to review

- **WHEN** the route step reads a revision draft with the label `needs-design`
- **THEN** it records the labels and change and prints the route `revised`, and the sketch agent doesn't run

#### Scenario: Two sketches at the first check

- **WHEN** a revision draft with `needs-design` has only `sketches/a.html` and `sketches/c.html`
- **THEN** the draft check exits with a failure, before any review

#### Scenario: An unsafe sketch in a revision

- **WHEN** a revision's `sketches/c.html` has a script
- **THEN** the draft check exits with a failure naming `sketches/c.html`
