Tasks marked done were completed on the `fabro-setup` branch before this proposal was written; they still need the review that the rest of the change gets.

## 1. Worktree and project setup

- [x] 1.1 Create the worktree with `git worktree add -b change/add-fabro-runs ../nycnoise-add-fabro-runs main`. Then:
  - move `.fabro/` and this change directory into it, and remove them from the main checkout;
  - symlink `.env` and `logs/` from the main checkout;
  - give it its own database, `nycnoise_add_fabro_runs`, dumped from `nycnoise`;
  - delete the `fabro-setup` branch, which has no commits of its own (`git log main..fabro-setup` is empty); deleting it needs Nate's go-ahead, given by confirming this proposal.

  Verify with `git -C ../nycnoise-add-fabro-runs status`, which should show only these files, and with `git status` in the main checkout, which should show none of them.
- [x] 1.2 Run `fabro repo init` and verify `.fabro/project.toml` and `.fabro/workflows/hello/` exist
- [x] 1.3 Add `[run.scm]` with provider `github`, owner `natea` and repository `newenglandmusic` to `.fabro/project.toml`. Verify `fabro preflight claude-max` reports the repository as natea/newenglandmusic, or an origin mismatch instead of nycnoise/nycnoise, and that `fabro preflight hello --environment local` still passes. Record both outputs here. (Done: `claude-max` preflight reports "Repository (natea/newenglandmusic)" and origin https://github.com/natea/newenglandmusic; its only failure is repository access for branch `change/add-fabro-runs`, which is not on the fork. `hello --environment local`: "All checks passed.")
- [x] 1.4 Add tests in `core/tests/test_fabro_config.py` for the "Project names the fork" and "A setting names upstream" scenarios. Verify they pass with `python manage.py test core.tests.test_fabro_config`, and that the second fails when an upstream name is added to a `.fabro/` file temporarily.

## 2. Hello workflow

- [x] 2.1 Turn off pull requests in `.fabro/workflows/hello/workflow.toml`, and verify `fabro preflight hello --environment local` shows no pull request error
- [x] 2.2 Replace the hello graph's prompt step with one command step (for example `git log -1 --oneline`), turn off run-branch pushing, and correct the comment about Daytona and the unused `draft` setting. Verify `fabro validate .fabro/workflows/hello/workflow.fabro` passes.
- [x] 2.3 Add tests for the "Hello workflow shape" scenario and the `hello` half of "Smoke-test settings", and verify they pass
- [x] 2.4 Manual check: run `fabro run hello --environment local` and verify it succeeds with no model and leaves the working tree unchanged. Record the run ID here. (Done: run 01M696CQQ3VPKGQPAHRB1TDR5D succeeded in 2 seconds with no model, working tree unchanged. An earlier run, 01M687YP6X73RSQ2DQZYW60HVF, used the old prompt step and OpenAI's gpt-5.4-mini.)

## 3. Daytona environment and claude-max workflow

- [x] 3.1 Add `.fabro/daytona.Dockerfile` (Node 22, git, Claude Code, the ACP adapter) and verify `fabro preflight claude-max` reports the Daytona sandbox as configured
- [x] 3.2 Add `.fabro/workflows/claude-max/` with one ACP Claude Code step and the `daytona` environment (vault token, empty API key, 30-minute idle stop, no pull request, no branch push), and verify `fabro preflight claude-max` passes everything except repository access
- [x] 3.3 Add tests for the "Token comes from the vault", "No token in the repo" (one general pattern for token-shaped values, such as `sk-ant-[a-z]+[0-9]*-[A-Za-z0-9_-]{20,}`, which catches subscription tokens and API keys alike, and which the spec and test files themselves don't match), "Lifecycle settings", "Claude-max workflow shape" and `claude-max` half of "Smoke-test settings" scenarios, and verify they pass

- [x] 3.4 Move the `daytona` environment out of `.fabro/workflows/claude-max/workflow.toml` into `.fabro/environments/daytona.json`, in the shape `POST /api/v1/environments` takes, with the Dockerfile inline; remove `[run.environment]` from the workflow and delete `.fabro/daytona.Dockerfile`. Verify the existing token and lifecycle tests, pointed at the JSON file, pass.
- [x] 3.5 Write `bin/fabro-environment`: create the environment when the server has none, replace it with `If-Match` when it does, and keep the dev token in a private header file. Verify by running it against the local server and checking that `GET /api/v1/environments/daytona` returns the file's settings. (Done: created, then replaced on a second run; the server's provider, resources, lifecycle, Dockerfile and env match the file, with the token as the vault reference.)
- [x] 3.6 Add tests with a stand-in `curl` for the "Environment missing on the server", "Environment already on the server" and "The dev token stays off command lines" scenarios, and verify they pass
- [x] 3.7 Set `on_failure="exit"` on both smoke workflows' graphs, and add a test for the "Failure policy" scenario
- [x] 3.8 Remove the Dockerfile from `.fabro/environments/daytona.json`, add the pinned install step to `claude-max` and switch its ACP command to `claude-agent-acp`, then update the "Claude-max workflow shape" test. Verify the config tests pass and `bin/fabro-environment` updates the server.

## 4. Credentials (Nate does these; no secret goes into the repo or a chat)

- [x] 4.1 Replace the expired `GITHUB_TOKEN` in Fabro's vault with a fresh fine-grained token that can read natea/newenglandmusic, or remove it, and verify `fabro doctor` no longer reports it invalid (done 31 October 2026: Nate stored a fine-grained token for natea/newenglandmusic only, with Contents and Pull requests read and write, ahead of the build workflow; `fabro doctor` reports it configured)
- [x] 4.2 Run `claude setup-token`, then `fabro secret set CLAUDE_CODE_OAUTH_TOKEN` with no value so Fabro prompts for it, and verify `fabro secret list` shows the secret (done 31 October 2026: `fabro secret list` shows CLAUDE_CODE_OAUTH_TOKEN as a token)

## 5. Manual checks of the sandbox path

- [x] 5.1 Before 4.2, or by temporarily renaming the reference, run `fabro run claude-max --environment daytona --target natea/newenglandmusic@main` and verify the Claude Code step fails naming the missing secret, no API key is used, and the run ends as failed (Done: run 01M699DPJGKYQDNHYGNJSN0CDW failed with "no secret named `CLAUDE_CODE_OAUTH_TOKEN_MISSING`". The earlier run 01M6994V09J0QCPY004PK2HF4G showed the step failing but the run reporting success, which led to task 3.7.)
- [x] 5.2 Run `fabro run claude-max --environment daytona --target natea/newenglandmusic@main`. Verify:
  - the run succeeds, and its file changes show `hello-claude-max.txt` with the expected text;
  - the run's details show the fork as the cloned repository;
  - no run branch appears on either GitHub repository;
  - the Daytona dashboard shows the sandbox stopped or deleted.

  Record the run ID here. (Run 01M6A82MA3ZC5R6XYE3YCG8HQT succeeded: the file changes hold the expected text, the cloned repository is natea/newenglandmusic, and neither GitHub repository has a run branch. The Daytona dashboard showed its sandbox still running 45 minutes later, and the failed runs' sandboxes stopped but not deleted; see the design's risks. Nate deleted it and the other leftover sandboxes by hand on 31 October 2026, as the guide now says to.)
- [x] 5.3 Run `fabro run claude-max --environment daytona` without `--target` from the worktree, and verify it stops with an origin mismatch and pushes nothing to nycnoise/nycnoise (Done, with origin's push address disabled for safety: it stopped before creating a run with "the workflow configures a run.scm repository that is not the local checkout's origin", and upstream has no branches from this change.)
- [x] 5.4 Check that the pinned versions in the install step are the ones 5.2 installed, from the run's log (Done: npm installed claude-code@2.1.316 and claude-agent-acp@0.99.1. npm skipped Claude Code's postinstall script; the ACP step doesn't need it.)

## 6. Guide and review

- [x] 6.1 Write `docs/FABRO.md`. It covers what Fabro is for here, the one-time token steps (4.2), the command for each workflow with `--environment local`, or `--environment daytona --target natea/newenglandmusic@main`, the `bin/fabro-environment` step, what each run proves, that the preflight warning about ignored pull request settings is expected, and that leftover `petri-<run id>-I0` sandboxes must be deleted in the Daytona dashboard (Jazkarta organization) after a run, because Fabro 0.400 leaves them.
- [x] 6.2 Add a test for the "Guide commands name the fork" and "Guide covers both workflows and the token" scenarios, and verify it passes
- [x] 6.3 Manual check: follow `docs/FABRO.md` from a fresh clone of the fork with the Fabro server running, and verify both workflows run without other instructions (Done 31 October 2026 from a clone of the branch: `bin/fabro-environment`, then hello run 01M6ABQR73J5MR0W12RB5W52YW and claude-max run 01M6ABQSMRZ8KHQVCDQXEDWJK9 both succeeded.)
- [x] 6.4 Run the full test suite with `python manage.py test` and verify it passes (Done 1 November 2026, 00:16 New York: all 1,380 tests pass. Before midnight, core.tests.test_sitemap and core.tests.test_index_geo_filter fail on the last evening of a month because they mix UTC and New York months; they fail the same way on main.)
