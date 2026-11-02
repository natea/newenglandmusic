## Context

See proposal.md for why. What the workflows must fit, checked on 2 November 2026:

- **The intentable bridge** (natea/intentable, `bridge/`, deployed on the DGX Spark) starts a run for an intake user's new issue (`triage`) or reply to a `state:needs-info` issue (`clarify`), over Fabro's API:
  - it reads `.fabro/workflows/<name>/` from the fork's default branch, or from `FABRO_WORKFLOW_REF`;
  - it uses the `daytona` environment, with the run's target, and so the sandbox's code, at the default branch's head (`bridge/src/workflow.ts`);
  - it passes the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author` and `issue_thread` as text, `issue_thread` being every comment so far as JSON `[{author, body}]`;
  - it does not pass the issue's labels;
  - it labels the run `issue=<number>`.
- **The bridge's own comments are in `issue_thread`.** They are posted with Nate's token, so their author is `natea`, and each ends with the hidden bridge marker `<!-- intentable-bridge -->`. Some are the agent's earlier questions or summaries, others status notes ("couldn't start", run links).
- **When a run succeeds,** the bridge reads the latest `.intentable/result.json` among the run's artifacts:
  - it applies its `labels`, each replacing any label of its group;
  - it moves the issue to `state`;
  - it posts `message`.

  It refuses state labels and unknown labels, and allows only the moves triage → needs-info, spec-review or parked, and needs-info → needs-info or spec-review. It accepts every issue label, including `P1–P5`, `needs-design` and `ai-shippable`.
- **The bridge's issue labels** (`bridge/src/labels.ts`):
  - `type:bug|feature|refactor|chore|spike`;
  - `clarity:1–5`, `risk:1–5`, `blast:1–5`;
  - `size:XS|S|M|L|XL`;
  - `P1–P5`, `needs-design` and `ai-shippable`.
- **Fabro 0.400:**
  - it reads the `workflow.toml` beside the registered graph as the workflow's settings, so `[run.inputs]`, `[run.artifacts]`, `[run.pull_request]` and `[run.run_branch]` apply to bridge-started runs;
  - an unbound input is refused;
  - `prompt="@prompt.md"` loads a prompt beside the graph, and prompts render `{{ inputs.NAME }}`, which isn't re-templated;
  - a human gate is a `shape=hexagon` step;
  - artifacts are collected after each stage, and the same path and content are recorded once;
  - a sandbox's git access is read-only by default (`fabro-petri/src/stage_credentials.rs`).
- **The `claude-max` smoke test** is the pattern for the agent: install `@anthropic-ai/claude-code@2.1.316` and `@agentclientprotocol/claude-agent-acp@0.99.1`, then an `agent` step with `backend="acp"`.

## Goals / Non-Goals

**Goals:**
- Every result the bridge receives is one it accepts, and one that moves the issue the right way. A wrong result fails the run instead, which the bridge reports as a stopped run.
- Everything that can be checked without a model is checked by Django tests.

**Non-Goals:**
- Judging the quality of the agent's labels or questions automatically. That is the live check's job, and Nate's.
- Rewriting the issue into Conor Luddy's template sections, which belongs to the spec stage.

## Decisions

**Runs end with their result; no human gates (Nate's decision, 2 November 2026).** A question is the `message` of a `needs-info` result. The bridge posts it, and the next reply starts `clarify`, which reads the whole thread again. That is docs/plan.md's "one short run per new comment… so no run sits waiting for days". The alternative, a Fabro human gate per question, would hold a sandbox open for as long as the person takes to answer.

**The agent reads the code, and nothing is pushed (Nate's decision, 2 November 2026).**
- The run's workspace is the repository at the run's target, so the agent can see which models, templates and views a request touches before guessing risk, blast radius and size.
- `run.pull_request.enabled = false` and `run.run_branch.push = false` stop Fabro pushing or opening anything.
- The sandbox's git access is read-only, so the agent can't push either. That holds while a workflow asks Fabro for no GitHub permissions in its run integrations (`stage_credentials.rs`), which the "Nothing pushed" test pins. It does keep network access and the Claude token, as every run does.
- The prompt tells it to change no file but the result. Anything else it writes stays in the sandbox, which the bridge deletes when the run succeeds.

**`parked` means what docs/plan.md says (Nate's decision, 2 November 2026).** Triage parks only a grey-area issue, where it's unclear whether the behaviour belongs in the site's spec, and its message says why, for Nate to decide. Anything else unclear, including something that may not be a request for the site, gets one question.

**A test branch is tested whole (Nate's decision, 2 November 2026).** For the live check, the bridge's `FABRO_WORKFLOW_REF` must also set the run's target to that branch, so the workflows and `bin/check-intentable-result` come from the same commit. That is a small change in natea/intentable, proposed separately, and a prerequisite of the live check only. The guide's hand trial passes `--target natea/newenglandmusic@<branch>` for the same reason.

**The OpenSpec explore stance (docs/plan.md, decided 30 October).** Both prompts tell the agent to behave as in OpenSpec's explore mode:
- curious and investigating;
- reading the code to ground its guesses;
- offering options to the person rather than prescribing;
- never writing code or building anything.

**One capability, two workflows (agent's decision).** Triage and clarify share inputs, result, checker and rules, and differ only in the labels and states they may give. `issue-triage` holds both. They are two workflows because the bridge starts them by name.

**A prompt file per workflow (agent's decision).** Each folder holds its own `prompt.md`, loaded with `prompt="@prompt.md"`, since the bridge's contract keeps the files Fabro reads inside the workflow's folder. The two prompts repeat the shared rules instead of including a shared file, so each folder stands alone. No prompt names the upstream repository, which the configuration tests forbid under `.fabro/`.

**What the prompts tell the agent:**
- **Who it's talking to:** the person who asked, who isn't a developer. Plain words, no code, no mentions. The prompts name roles, not people.
- **What it gets:** the issue's title, body, author and thread. A comment ending with `<!-- intentable-bridge -->` is the bridge's, posted under the `natea` account: its own earlier questions, or status notes. It isn't the owner speaking.
- **What triage gives:** exactly one `type:`, `clarity:`, `risk:`, `blast:` and `size:` label, and no other label.
- **What clarify gives:** an updated `clarity:` label, judged afresh from the whole thread, since the bridge doesn't pass current labels. It may also give one of each of type, risk, blast and size, if the answers change them, and no other label.
- **The clarity rule:**
  - 4 or 5 means clear enough to write up: `spec-review`, with two to four sentences summarising what will be built (agent's decision on length), ending with "Next, this will be written up as a proposal for Nate to review before anything is built." (Nate's wording, 2 November 2026, after the live check showed the summary left the person without a next step; the checker requires it);
  - 1 to 3 means `needs-info`, with exactly one question, the one whose answer would raise clarity most;
  - triage alone may use `parked`, for a grey-area issue, saying why.
- **The question:** end with the single question. Put no other `?` in the message, not even inside a link.
- **The result:** write `.intentable/result.json` in the workspace root, and change no other file.

**A checker as the last step (agent's decision).** `bin/check-intentable-result <triage|clarify> [path]` is a Python script with no dependencies. It reads the result and exits non-zero with a plain reason when the result:
- breaks the bridge's rules;
- carries a later-stage label (`P1–P5`, `needs-design`, `ai-shippable`);
- has a state that doesn't fit its clarity;
- has a message that is missing, asks other than one question (`needs-info`), mentions a user (`@` followed by a login), or is longer than 2,000 characters.

Because the graph has `on_failure="exit"`, a bad result fails the run instead of reaching the issue. Python, because Django's tests can run it directly; the install step prints `python3 --version` first, so a sandbox without Python fails clearly. It holds its own copy of the bridge's label list. A test pins that list, as a change detector, since the bridge is in another repository.

**`think` writes the result, and `check` runs after it (agent's decision).** The bridge's contract and dictionary say the result is written "in its last step". Here the last step only checks it. Artifacts are collected after every stage, and an unchanged file is recorded once, so the bridge reads the same file. The bridge's README and dictionary get a follow-up to say "the last step that writes files".

**The step order:** `start → install → think → check → exit`. `think` is the ACP agent step. `check` runs `python3 bin/check-intentable-result triage` or `clarify`. It names no input, so issue text never reaches a command.

**Inputs default to empty text (agent's decision).** `[run.inputs]` declares the five with `""` defaults, so a hand-started run isn't refused. The bridge always passes all five.

**Testing:** `core/tests/test_issue_triage.py`, as `SimpleTestCase`s:
- the configuration scenarios read the workflow files, with the `workflow()` reader from `test_fabro_config.py`;
- the checker scenarios run `bin/check-intentable-result` in a temporary folder on fixture results, an otherwise complete result each time;
- the guide scenario reads `docs/FABRO.md`.

No test calls Fabro, Daytona, GitHub or a model. The agent's judgment gets a live check on the Spark (tasks).

## Risks / Trade-offs

- **Issue text goes into the agent's prompt.** A request could try to instruct the agent. → Only intake users can start runs, and nothing can be pushed. The checker limits what reaches the issue: known first-guess labels, never `ai-shippable` or a priority, allowed states, and a short message with no mentions.
- **The agent may ask through a question tool** instead of ending with a result. → The bridge's question relay would post it and the run would wait, which Nate ruled out. Fabro's log on the Spark shows its run tools aren't registered on these runs, but how Claude Code's own question tool behaves over ACP is unconfirmed. The live check watches for it.
- **A session has no turn or time limit.** → A stuck run is ended by the bridge's sandbox limits: 30 idle minutes, 180-minute lifetime. The live check records how long a run takes.
- **One question is approximated as one `?`.** → The prompt says to keep `?` out of links and quotes. The live check reads the messages.
- **A mention is approximated as `@` plus a login at a word start.** → An email address passes; a mention written another way would get through, and the live check reads the messages.
- **The label list is in two places.** → A test pins the checker's copy, and the bridge's README will say a label change needs the checker changed too.
- **During the live check,** every issue or reply from anyone on the intake list runs the change branch's workflows. → The check names the window, and lists the open issues catch-up will triage when the bridge restarts.
- **A real run costs** Max-subscription usage and a Daytona sandbox for a few minutes. → Only intake users start runs, and each run ends.

## Migration Plan

1. **The live check,** after the intentable change that makes the test branch the target, and with Nate's go-ahead for each outward step: push this branch to the fork, point the Spark's bridge at it, run the check, then point it back and delete the pushed branch.
2. **After Nate's G4:** archive the change, merge into `main`, and push `main` to natea/newenglandmusic with his go-ahead. That push also makes Render deploy the site. The bridge reads the default branch, so the workflows take effect then.

**Rollback:** delete the two workflow folders from the fork's `main`. The bridge then answers "the agent couldn't start" again.

## Open Questions

none
