### running agents with fabro

[Fabro](https://fabro.sh) runs agent workflows for this repo: each run gets a sandbox, a branch and a record of what happened. It's the start of the loop in intentable's plan, where agents pick up GitHub issues. For now there are two smoke tests, which check that the setup works:

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
