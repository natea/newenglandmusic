## Context

See proposal.md for why. The local Fabro server runs on Nate's Mac. It has the `local` environment, Docker running and a Daytona key in its vault. Its stored GitHub token has expired and its Anthropic API key is invalid. Daytona sandboxes run in Nate's Jazkarta organization; his personal Daytona organization is suspended for depleted credits, which is why the April key could look snapshots up but not create them. The checkout's `origin` remote is the upstream nycnoise/nycnoise; the fork is the `github` remote, natea/newenglandmusic, and it is public. The repo's OpenSpec context forbids pushing or opening pull requests upstream.

**Fabro upgrade and secrets conversion (done before this proposal, without Nate's go-ahead beyond "probably needs to be updated").** On 31 October 2026 the agent upgraded Fabro from 0.234 to 0.400.0-nightly.0 and fast-forwarded `~/Documents/code/fabro`. The 0.400 server refused to start, because it could not read the vault file `~/.fabro/storage/vaults/default/secrets.json`: entries of the old types `environment` and `credential` are no longer accepted. The agent copied the file to `secrets.json.pre-0.400-backup` beside it, then rewrote it:
- `environment` entries became `token` entries with the same names;
- the `anthropic`, `openai` and `gemini` `credential` entries became `token` entries named `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `GEMINI_API_KEY`, holding the same key values.

On start, the server imported all six secrets into its database and renamed the file; `fabro doctor` confirmed the Daytona, Brave and OpenAI keys work. No secret was dropped. Nate should confirm this at the proposal gate (G2).

**How Fabro picks the repository.** Workflows.mdx in the Fabro docs, and the manifest code, say:
- A Daytona run with no target flag uses the checkout's `origin`, and may push the checked-out branch there so the sandbox can clone its commit.
- If `[run.scm]` in the workflow or project settings names a repository that does not match `origin`, Fabro skips the push and stops the run instead.
- `--target OWNER/REPO[@BRANCH]` overrides both.
- A local-environment run, such as `hello`, uses the checkout folder as its target before any `[run.scm]` check, so the setting doesn't affect it; Fabro rejects `--target` for local runs.
- Fabro bundles the workflow files from the local checkout, so they need not be pushed.
- `fabro preflight` has no target flag. It checks repository access against `origin` with a read-only `git ls-remote`, which does contact upstream.

## Goals / Non-Goals

**Goals:**
- Prove the two pieces the later workflows depend on: Fabro running in this repo, and Claude Code in a Daytona sandbox on the Max subscription.
- A run started from this checkout can't push to upstream by mistake: it either targets the fork or stops.

**Non-Goals:**
- No site preview, GitHub App, webhook or bridge work.
- The `daytona` image is not for running Django. The build workflow needs Python 3.11, Postgres and the repo's dependencies, and gets its own image.

## Decisions

**Claude Code through ACP, authenticated with a subscription token (Nate's decision to use the Max plan).** Fabro's own prompt stages call model APIs directly and need an API key. Claude Code run through the ACP adapter uses whatever login Claude Code has. On the Mac that is the keychain login, which the earlier claude-acp test used by setting `ANTHROPIC_API_KEY` empty. In a Daytona sandbox there is no keychain. Instead:
- `claude setup-token` creates a subscription token, which Nate stores in Fabro's vault as `CLAUDE_CODE_OAUTH_TOKEN`.
- The environment passes it into the sandbox through `{{ secrets.NAME }}` interpolation.
- Fabro's docs (environments.mdx, run-configuration.mdx) say a missing or non-token secret fails closed. The first live check (run 01M6994V09J0QCPY004PK2HF4G) showed when: Fabro starts the sandbox first, then fails the Claude Code step with "no secret named …". It never falls back to an API key, which is what matters, but a sandbox is created and then stopped.

The tests check the exact reference and the empty API key, which is what makes the fail-closed behavior apply.

**A failed step fails the run (found in the first live check).** Fabro's default failure policy, `route`, sends a failed step down its unconditional edge, so the `claude-max` run with a missing secret reached exit and reported success. Both smoke workflows set `on_failure="exit"` on the graph, so a failed step ends the run as failed. The bridge's later workflows need the same policy, or explicit failure edges.

**`hello` uses a shell command, not a model (agent's decision, for Nate to confirm at G2).** The first `hello` run used OpenAI's gpt-5.4-mini, because the starter workflow has a prompt step and the Anthropic key is invalid. That used an API key, against Nate's decision to use the Max plan. The `claude-max` workflow already tests the model path, so `hello` only needs to prove the server and repo setup. It becomes a single command step, and uses no provider or key. Alternative: an ACP Claude Code step on the Mac's keychain login, rejected because it needs the ACP adapter installed on the Mac and duplicates `claude-max`.

**`[run.scm]` names the fork; `--target` in the guide; a text check as backup (agent's decision).** Each approach has a weakness:
- `--target` alone depends on remembering it.
- A test that searches `.fabro/` for the upstream name cannot catch a bare run, because the upstream target comes from `origin`, not from a file.
- Renaming the remotes so `origin` is the fork changes every developer's local Git setup, and is easy to lose in a new clone.

`[run.scm]` with provider `github`, owner `natea` and repository `newenglandmusic` in `.fabro/project.toml` makes a bare Daytona run from this checkout stop with an origin mismatch instead of pushing upstream. The guide's commands pass `--target natea/newenglandmusic@<branch>`, and the text check stays as a second guard. Renaming the remotes remains a convenience Nate can choose locally.

**The environment lives in the repo as an API request body, and a script puts it on the server (Nate's choice, 31 October 2026, from three options).** The first plan defined `[environments.daytona]` in the workflow's settings. That passed `fabro validate` and `fabro preflight`, but `fabro run` ignores it: Fabro 0.400 runs only in environments stored on the server, picked by `--environment` or named `default` (fabro-cli `commands/run/create.rs`, `resolve_run_environment`). With the table in `.fabro/project.toml`, preflight also could not find it at all. Three options were weighed:
- **Chosen:** keep the definition in `.fabro/environments/daytona.json` as the exact body of `POST /api/v1/environments`, and have `bin/fabro-environment` create or replace it on the server. Runs pass `--environment daytona`. The tests keep checking the token, the empty API key and the lifecycle by reading the JSON, so the spec still covers them.
- Create the environment once by hand in Fabro's web UI. That is quicker, but the repo would hold no definition and those scenarios could not be tested.
- The chosen route, but naming the environment `default`, so runs need no flag. Rejected because every Fabro run on Nate's server, from any repo, would then land in this small sandbox.

The script uses `curl` and `jq`. It reads the server's address from `FABRO_SERVER` (default `http://127.0.0.1:32276`) and the dev token from `FABRO_DEV_TOKEN` or `~/.fabro/dev-token`. It writes the token into a private temporary header file, so the token never appears in a process list or in output. It asks for the environment first: on a 404 it creates it with the whole file, and otherwise it replaces it with the file minus `id`, sending the returned `ETag` as `If-Match`, as the API requires.

**Daytona rather than Modal (agent's decision, following Nate's options).** Nate named both Daytona and Modal for sandboxes. Fabro's preview links work only with Daytona, which the plan relies on for site previews, and a Daytona key is already in the vault. In Fabro, the Modal integration is a model provider, not a sandbox.

**Smoke tests target `main` (agent's decision).** The smoke tests read nothing from the branch under development, so targeting `main` avoids pushing the work branch just to run them.

**Claude Code is installed at the start of each run (Nate's choice, 31 October 2026, from two options).** The live check showed that Fabro 0.400 ignores an environment's Dockerfile: the sandbox's runner reads only `image.docker`, a ready-made image reference (Fabro's `petri_runs.rs`), and the sandbox came up on Daytona's default image, which has Node and npm but not Claude Code. Two options were weighed:
- **Chosen:** a command step before the Claude Code step runs `npm install -g` for `@anthropic-ai/claude-code` and `@agentclientprotocol/claude-agent-acp` at exact versions (2.1.316 and 0.99.1 at the time of writing). The ACP adapter's old package, `@zed-industries/claude-code-acp`, is deprecated in favour of this one, whose command is `claude-agent-acp`. It installs with `--prefix /usr/local`, because npm's own global folder in Daytona's image (`/opt/hostedtoolcache/node/…`) is not on the PATH the agent process gets. Each run spends 30 to 60 seconds installing; nothing needs publishing.
- Build an image with both preinstalled, push it to GitHub's container registry, and reference it with `image.docker`. Runs start faster, but it needs a build-and-push setup and a published package. It is the likely route for the build workflow, whose Python, Postgres and repo dependencies would be slow to install every run.

The environment file therefore names no image, and keeps the resources, lifecycle and env. The 2 CPUs, 4 GB and 10 GB are enough for one agent writing a file. Daytona bills running sandboxes by the second, so the idle stop is 30 minutes instead of Fabro's default 120. Fabro's runner doesn't read the lifecycle either; the server applies it, which the live run checks on the Daytona dashboard.

**Testing.** Workflows run real models in real sandboxes, which tests must not do. Every spec scenario is a property of checked-in files, or of what `bin/fabro-environment` sends, tested with Django `SimpleTestCase`s in `core/tests/test_fabro_config.py`. The script's tests put a stand-in `curl` first on `PATH` that records its arguments and plays back a 404 or an existing environment, the way `test_scheduled_jobs` stands in for Python; no request reaches a Fabro server. They read the TOML with `tomllib` and the graphs and the guide as text, and need no database. Fabro, Daytona, GitHub and Anthropic are never contacted in tests: there is nothing to mock, because the tests call no service. The live runs (`hello`, the missing-token check, `claude-max`, and following the guide from a fresh clone) are manual verification tasks in tasks.md, not spec scenarios. They confirm that Fabro honors these settings; their run IDs are recorded there.

## Risks / Trade-offs

- **The Max plan's terms may not allow a shared, unattended loop.** → Use it for the smoke test and early runs only. Decide with the intentable plan's open decision before the loop runs for Sooz and Mark.
- **The token is a plain environment variable in the sandbox, and the network is open by default, so anything the agent runs can read it.** → Acceptable for a smoke test that runs no repo code. The build, clarify and preview changes run repo code and package install scripts, so they need a network allow-list or a way to keep the token out of those steps.
- **The expired GitHub token breaks the sandbox clone.** Fabro writes the stored token into the sandbox's Git credentials, and GitHub rejects bad credentials even for a public repo. → Replacing or removing it is a task before the first Daytona run.
- **Preflight warns that `[run.pull_request]` and `[run.run_branch]` are ignored "by the standalone runner".** The server worker does read them, so the warning is expected. → The guide says so, and the manual `claude-max` run confirms no branch was pushed.
- **The Daytona snapshot build fails or is slow on the first run.** → The first run may take several minutes. A failure shows in the run log, and the image can change without changing the spec.
- **The ACP adapter package is renamed or changes its command.** → The install step pins exact versions.
- **Fabro 0.400 doesn't apply the environment's lifecycle.** Observed on 31 October 2026: the sandbox of the successful run 01M6A82MA3ZC5R6XYE3YCG8HQT was still running 45 minutes after the run ended, despite `stop_on_terminal` and a 30-minute idle stop. The sandboxes of failed runs were stopped, but none was deleted, despite `preserve = false`. The config tests can't catch this, since they check the file, not Fabro. → The guide says to delete leftover `petri-<run id>-I0` sandboxes in the Daytona dashboard after a run. Stopping sandboxes from outside Fabro, for instance from the bridge, which watches every run, is left to a later change.

## Migration Plan

Nothing to migrate. Rollback: delete `.fabro/`, `bin/fabro-environment`, the test module and the guide, the `daytona` environment on the server, and the `CLAUDE_CODE_OAUTH_TOKEN` secret. To undo the secrets conversion on the Fabro side, restore `secrets.json.pre-0.400-backup` and reinstall Fabro 0.234.
