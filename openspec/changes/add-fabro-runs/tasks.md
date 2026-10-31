Tasks marked done were completed on the `fabro-setup` branch before this proposal was written; they still need the review that the rest of the change gets.

## 1. Worktree and project setup

- [ ] 1.1 Create the worktree with `git worktree add -b change/add-fabro-runs ../nycnoise-add-fabro-runs main`. Then:
  - move `.fabro/` and this change directory into it, and remove them from the main checkout;
  - symlink `.env` and `logs/` from the main checkout;
  - give it its own database, `nycnoise_add_fabro_runs`, dumped from `nycnoise`;
  - delete the `fabro-setup` branch, which has no commits of its own (`git log main..fabro-setup` is empty); deleting it needs Nate's go-ahead, given by confirming this proposal.

  Verify with `git -C ../nycnoise-add-fabro-runs status`, which should show only these files, and with `git status` in the main checkout, which should show none of them.
- [x] 1.2 Run `fabro repo init` and verify `.fabro/project.toml` and `.fabro/workflows/hello/` exist
- [ ] 1.3 Add `[run.scm]` with provider `github`, owner `natea` and repository `newenglandmusic` to `.fabro/project.toml`. Verify `fabro preflight claude-max` reports the repository as natea/newenglandmusic, or an origin mismatch instead of nycnoise/nycnoise, and that `fabro preflight hello --environment local` still passes. Record both outputs here.
- [ ] 1.4 Add tests in `core/tests/test_fabro_config.py` for the "Project names the fork" and "A setting names upstream" scenarios. Verify they pass with `python manage.py test core.tests.test_fabro_config`, and that the second fails when an upstream name is added to a `.fabro/` file temporarily.

## 2. Hello workflow

- [x] 2.1 Turn off pull requests in `.fabro/workflows/hello/workflow.toml`, and verify `fabro preflight hello --environment local` shows no pull request error
- [ ] 2.2 Replace the hello graph's prompt step with one command step (for example `git log -1 --oneline`), turn off run-branch pushing, and correct the comment about Daytona and the unused `draft` setting. Verify `fabro validate .fabro/workflows/hello/workflow.fabro` passes.
- [ ] 2.3 Add tests for the "Hello workflow shape" scenario and the `hello` half of "Smoke-test settings", and verify they pass
- [ ] 2.4 Manual check: run `fabro run hello --environment local` and verify it succeeds with no model and leaves the working tree unchanged. Record the run ID here. (An earlier run, 01M687YP6X73RSQ2DQZYW60HVF, used the old prompt step and OpenAI's gpt-5.4-mini.)

## 3. Daytona environment and claude-max workflow

- [x] 3.1 Add `.fabro/daytona.Dockerfile` (Node 22, git, Claude Code, the ACP adapter) and verify `fabro preflight claude-max` reports the Daytona sandbox as configured
- [x] 3.2 Add `.fabro/workflows/claude-max/` with one ACP Claude Code step and the `daytona` environment (vault token, empty API key, 30-minute idle stop, no pull request, no branch push), and verify `fabro preflight claude-max` passes everything except repository access
- [ ] 3.3 Add tests for the "Token comes from the vault", "No token in the repo" (one general pattern for token-shaped values, such as `sk-ant-[a-z]+[0-9]*-[A-Za-z0-9_-]{20,}`, which catches subscription tokens and API keys alike, and which the spec and test files themselves don't match), "Lifecycle settings", "Claude-max workflow shape" and `claude-max` half of "Smoke-test settings" scenarios, and verify they pass

## 4. Credentials (Nate does these; no secret goes into the repo or a chat)

- [x] 4.1 Replace the expired `GITHUB_TOKEN` in Fabro's vault with a fresh fine-grained token that can read natea/newenglandmusic, or remove it, and verify `fabro doctor` no longer reports it invalid (done 31 October 2026: Nate stored a fine-grained token for natea/newenglandmusic only, with Contents and Pull requests read and write, ahead of the build workflow; `fabro doctor` reports it configured)
- [x] 4.2 Run `claude setup-token`, then `fabro secret set CLAUDE_CODE_OAUTH_TOKEN` with no value so Fabro prompts for it, and verify `fabro secret list` shows the secret (done 31 October 2026: `fabro secret list` shows CLAUDE_CODE_OAUTH_TOKEN as a token)

## 5. Manual checks of the sandbox path

- [ ] 5.1 Before 4.2, or by temporarily renaming the reference, run `fabro run claude-max --target natea/newenglandmusic@main` and verify the run fails before a sandbox starts, naming the missing secret
- [ ] 5.2 Run `fabro run claude-max --target natea/newenglandmusic@main`. Verify:
  - the run succeeds, and its file changes show `hello-claude-max.txt` with the expected text;
  - the run's details show the fork as the cloned repository;
  - no run branch appears on either GitHub repository;
  - the Daytona dashboard shows the sandbox stopped or deleted.

  Record the run ID here.
- [ ] 5.3 Run `fabro run claude-max` without `--target` from the worktree, and verify it stops with an origin mismatch and pushes nothing to nycnoise/nycnoise
- [ ] 5.4 Pin the npm package versions in `.fabro/daytona.Dockerfile` to the versions 5.2 used, and verify the next run builds the new snapshot without errors

## 6. Guide and review

- [ ] 6.1 Write `docs/FABRO.md`. It covers what Fabro is for here, the one-time token steps (4.2), the command for each workflow with `--environment local` or `--target natea/newenglandmusic@main`, what each run proves, and that the preflight warning about ignored pull request settings is expected.
- [ ] 6.2 Add a test for the "Guide commands name the fork" and "Guide covers both workflows and the token" scenarios, and verify it passes
- [ ] 6.3 Manual check: follow `docs/FABRO.md` from a fresh clone of the fork with the Fabro server running, and verify both workflows run without other instructions
- [ ] 6.4 Run the full test suite with `python manage.py test` and verify it passes
