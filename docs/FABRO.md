### running agents with fabro

[Fabro](https://fabro.sh) runs agent workflows for this repo: each run gets a sandbox, a branch and a record of what happened. It's the start of the loop in intentable's plan, where agents pick up GitHub issues. Two workflows sort and clarify those issues (see below), and two smoke tests check that the setup works:

- `hello` runs one shell command on your Mac, with no model. It proves the Fabro server and this repo's `.fabro/` setup work.
- `claude-max` runs Claude Code in a Daytona sandbox, signed in with Nate's Claude Max subscription instead of an API key. It proves a sandbox can clone the fork, install Claude Code and let it write a file.

Neither pushes a branch or opens a pull request.

#### before your first run

You need the Fabro server running (`fabro server start`) and `fabro doctor` passing for GitHub and Daytona.

1. Create a Claude subscription token and store it in Fabro's vault. Leave the value off the command line: Fabro asks for it, so it stays out of your shell history.

   ```bash
   claude setup-token
   fabro secret set CLAUDE_CODE_OAUTH_TOKEN
   ```

2. Put the `daytona` environment on the Fabro server. Fabro only runs environments stored on the server, and this copies `.fabro/environments/daytona.json` there. Run it again whenever that file changes.

   ```bash
   bin/fabro-environment
   ```

The Daytona key in Fabro's vault belongs to the Jazkarta organization in Daytona; Nate's personal organization is out of credits.

#### running the smoke tests

```bash
fabro run hello --environment local
fabro run claude-max --environment daytona --target natea/newenglandmusic@main
```

- `--environment daytona` picks the server's sandbox environment. Fabro ignores an environment named in a workflow's own settings.
- `--target natea/newenglandmusic@main` makes the sandbox clone the fork. This checkout's `origin` is the upstream nycnoise/nycnoise, which we never push to; `.fabro/project.toml` names the fork, so a run without `--target` stops instead of falling back to upstream.
- `hello` takes no `--target`: local runs work from this checkout's committed files, and Fabro refuses a target for them.

A `claude-max` run takes about two minutes, most of it starting the sandbox and installing Claude Code. Fabro prints a warning that `run.pull_request` and `run.run_branch` settings are ignored "by the standalone runner"; that's expected, because the server does apply them.

#### after a claude-max run

Fabro 0.400 doesn't stop or delete a sandbox when the run ends. Open the Daytona dashboard (Jazkarta organization), find the sandbox named `petri-<run id>-I0` and delete it, or it keeps billing.

#### triage and clarify

These two workflows are started by the intentable bridge (natea/intentable), never by hand in normal use. The bridge runs them on the Fabro server on the DGX Spark, in the `daytona` environment, for issues on natea/newenglandmusic opened or answered by someone on its intake list. Both run Claude Code on Nate's Max subscription, read this repo's code, push nothing and open no pull request, and end with a result instead of waiting for anyone.

##### triage

Started when someone on the intake list opens an issue. Claude Code reads the issue and the code, then gives first-guess labels: one each of type, clarity, risk, blast radius and size. It then moves the issue on:

- clarity 4 or 5: `spec-review`, with a short summary of what would be built, ending "Next, this will be written up as a proposal for Nate to review before anything is built.";
- clarity 1 to 3: `needs-info`, with one question;
- a grey-area issue, where it's unclear whether the behaviour belongs in the site's spec: `parked`, with the reason, for Nate to decide.

##### clarify

Started when someone on the intake list replies to an issue labelled `state:needs-info`. Claude Code reads the whole thread and judges clarity afresh, then either asks the next single question or moves the issue to `spec-review` with its summary.

##### the result

Each run writes `.intentable/result.json`, which the bridge reads from the run's artifacts:

```json
{"labels": ["type:feature", "clarity:2", "risk:2", "blast:2", "size:M"], "state": "needs-info", "message": "Should the venue page show past shows as well as upcoming ones?"}
```

The last step, `bin/check-intentable-result triage` (or `clarify`), refuses a result the bridge would refuse or that breaks the rules: labels for later stages (`P1`–`P5`, `needs-design`, `ai-shippable`), a state that doesn't fit the clarity, or a message that asks more or less than one question, mentions someone or runs past 2,000 characters. A refused result fails the run, and the bridge tells the issue the agent stopped. Run it on a result by hand with `bin/check-intentable-result triage path/to/result.json`.

##### trying one on a branch

To try a change to these workflows before it reaches `main`, push the branch to the fork and run it against the same branch, so the workflow and the checker come from one commit:

```bash
fabro run natea/newenglandmusic@<branch>:triage --environment daytona --target natea/newenglandmusic@<branch> \
  -I issue_number=0 -I issue_author=natea -I issue_title='Try the triage workflow' \
  -I issue_body='Show each venue page with its upcoming shows.' -I issue_thread='[]'
```

The bridge does the same when `FABRO_WORKFLOW_REF` is set on the Spark. A hand-started run's sandbox isn't deleted when it ends, but the bridge gives it the usual limits, so Daytona stops it after 30 idle minutes and destroys it within three hours.


#### spec

Started by the intentable bridge when a triage or clarify result moves an issue to `spec-review`, once per time the issue gets there. It writes the issue up as an OpenSpec proposal and has it reviewed, all in one sandbox, every agent being Claude Code through ACP on Nate's Max subscription:

1. **propose** reads the thread and the code and writes one OpenSpec change (proposal, delta specs, design, tasks), naming it in `.intentable/draft.json`. If the issue isn't clear enough after all, it writes no change and sends the issue back to `needs-info` with one question, skipping everything below.
2. **sketch**, only when the draft is labelled `needs-design`: Impeccable's decision step makes three self-contained HTML options in the change's `sketches/` folder, checked at once by `bin/check-intentable-result spec --sketches`.
3. **review**: three fresh reviewers in parallel, one lens each (risk, spec fit, fidelity), each writing a report and editing nothing.
4. **revise** applies the blocking findings and writes what it did and didn't do; the reviewers then read the revised text.

The loop ends when all three are satisfied in one round, or after the five-round limit, when the draft is still kept, marked not passed. `bin/check-intentable-reviews` keeps the rounds and writes the summary, whose first line is `Passed by the reviewers after <n> round(s).` or `Not passed by the reviewers after <n> rounds.`.

The last step, `bin/check-intentable-result spec`, copies the change into `.intentable/proposal/`, the summary to `.intentable/review.md`, and writes `.intentable/result.json` with the change's name, the message, `reviewed` and `files`. The run itself pushes nothing: the bridge commits the draft from those artifacts to `change/<name>` on the fork, which publishes its Spek page and, beside it, its sketches.

Try it on a branch the same way as triage, with `:spec` and an issue that is clear enough to write up.
