## Context

See proposal.md for why. The local Fabro server runs on Nate's Mac. It has the `local` environment, Docker running and a Daytona key in its vault. Its stored GitHub token has expired and its Anthropic API key is invalid. The checkout's `origin` remote is the upstream nycnoise/nycnoise; the fork is the `github` remote, natea/newenglandmusic, and it is public. The repo's OpenSpec context forbids pushing or opening pull requests upstream.

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
- Fabro's docs (environments.mdx, run-configuration.mdx) say a missing or non-token secret fails closed before the sandbox starts.

The tests check the exact reference and the empty API key, which is what makes the fail-closed behavior apply.

**`hello` uses a shell command, not a model (agent's decision, for Nate to confirm at G2).** The first `hello` run used OpenAI's gpt-5.4-mini, because the starter workflow has a prompt step and the Anthropic key is invalid. That used an API key, against Nate's decision to use the Max plan. The `claude-max` workflow already tests the model path, so `hello` only needs to prove the server and repo setup. It becomes a single command step, and uses no provider or key. Alternative: an ACP Claude Code step on the Mac's keychain login, rejected because it needs the ACP adapter installed on the Mac and duplicates `claude-max`.

**`[run.scm]` names the fork; `--target` in the guide; a text check as backup (agent's decision).** Each approach has a weakness:
- `--target` alone depends on remembering it.
- A test that searches `.fabro/` for the upstream name cannot catch a bare run, because the upstream target comes from `origin`, not from a file.
- Renaming the remotes so `origin` is the fork changes every developer's local Git setup, and is easy to lose in a new clone.

`[run.scm]` with provider `github`, owner `natea` and repository `newenglandmusic` in `.fabro/project.toml` makes a bare Daytona run from this checkout stop with an origin mismatch instead of pushing upstream. The guide's commands pass `--target natea/newenglandmusic@<branch>`, and the text check stays as a second guard. Renaming the remotes remains a convenience Nate can choose locally.

**The environment is defined in the workflow's own settings (agent's decision).** With the `[environments.daytona]` table in `.fabro/project.toml`, both `fabro validate` and `fabro preflight claude-max` reported: "`[run.environment] id = "daytona"` ... names no `[environments.daytona]` table in any settings layer". Fabro's docs say project TOML may define environments, so this may be a Fabro bug. The table lives in `.fabro/workflows/claude-max/workflow.toml` for now. When a second Daytona workflow arrives, we move the definition to a server-managed environment through Fabro's environments API, or back to `project.toml` if a later Fabro fixes this.

**Daytona rather than Modal (agent's decision, following Nate's options).** Nate named both Daytona and Modal for sandboxes. Fabro's preview links work only with Daytona, which the plan relies on for site previews, and a Daytona key is already in the vault. In Fabro, the Modal integration is a model provider, not a sandbox.

**Smoke tests target `main` (agent's decision).** The smoke tests read nothing from the branch under development, so targeting `main` avoids pushing the work branch just to run them.

**A small image built from a Dockerfile (agent's decision).** The image is `node:22-bookworm` with git and the two npm packages: Claude Code and `@zed-industries/claude-code-acp`. Daytona builds it once into a snapshot keyed on the Dockerfile text, the resources and the key, and then reuses it. The resources are 2 CPUs, 4 GB memory and 10 GB disk, enough for one agent writing a file. Daytona bills running sandboxes by the second, so the idle stop is 30 minutes instead of Fabro's default 120: a smoke test needs a few minutes.

**Testing.** Workflows run real models in real sandboxes, which tests must not do. Every spec scenario is a property of checked-in files, tested with Django `SimpleTestCase`s in `core/tests/test_fabro_config.py`. They read the TOML with `tomllib` and the graphs and the guide as text, and need no database. Fabro, Daytona, GitHub and Anthropic are never contacted in tests: there is nothing to mock, because the tests call no service. The live runs (`hello`, the missing-token check, `claude-max`, and following the guide from a fresh clone) are manual verification tasks in tasks.md, not spec scenarios. They confirm that Fabro honors these settings; their run IDs are recorded there.

## Risks / Trade-offs

- **The Max plan's terms may not allow a shared, unattended loop.** → Use it for the smoke test and early runs only. Decide with the intentable plan's open decision before the loop runs for Sooz and Mark.
- **The token is a plain environment variable in the sandbox, and the network is open by default, so anything the agent runs can read it.** → Acceptable for a smoke test that runs no repo code. The build, clarify and preview changes run repo code and package install scripts, so they need a network allow-list or a way to keep the token out of those steps.
- **The expired GitHub token breaks the sandbox clone.** Fabro writes the stored token into the sandbox's Git credentials, and GitHub rejects bad credentials even for a public repo. → Replacing or removing it is a task before the first Daytona run.
- **Preflight warns that `[run.pull_request]` and `[run.run_branch]` are ignored "by the standalone runner".** The server worker does read them, so the warning is expected. → The guide says so, and the manual `claude-max` run confirms no branch was pushed.
- **The Daytona snapshot build fails or is slow on the first run.** → The first run may take several minutes. A failure shows in the run log, and the image can change without changing the spec.
- **The ACP adapter package is renamed or changes its command.** → Pin the versions in the Dockerfile once the first run passes.
- **A Daytona sandbox leaks after an interrupted run.** → `stop_on_terminal` plus the 30-minute idle stop. The manual run checks the Daytona dashboard by the run's label.

## Migration Plan

Nothing to migrate. Rollback: delete `.fabro/`, the test module and the guide, and the `CLAUDE_CODE_OAUTH_TOKEN` secret. To undo the secrets conversion on the Fabro side, restore `secrets.json.pre-0.400-backup` and reinstall Fabro 0.234.
