## Why

We want agents to build changes for this site from GitHub issues, with Sooz and Mark asking for features and checking results, and Nate approving. Fabro (fabro.sh) runs those agents as workflows with human gates, in Daytona sandboxes that can serve a preview. Before any real workflow can run, the repo needs Fabro set up, and we need to know whether Claude Code can run inside a sandbox on Nate's Claude Max subscription instead of an API key, as he asked.

This proposal is written after the fact: some of the setup in "What Changes" was done on the `fabro-setup` branch before a proposal existed. It records what that work was meant to do and what remains, so the rest goes through the normal change cycle. Where the earlier work went against a decision, design.md says so.

## What Changes

- Add Fabro's project configuration to the repo (`.fabro/project.toml`), naming the fork as the repository for every run, so that a run cannot fall back to the upstream `origin`.
- Add a `hello` workflow that runs one shell command on Nate's Mac, with no model, to check that the Fabro server and repo setup work.
- Add a `daytona` sandbox environment: a Node image with Claude Code and its ACP adapter, small resources, and a 30-minute idle stop. Claude Code signs in with a subscription token from Fabro's vault; the Anthropic API key is left empty.
- Add a `claude-max` workflow that runs Claude Code once in that sandbox to write a known file, and pushes nothing.
- Add tests that read the Fabro configuration and the guide and check the settings the spec names.
- Add a guide, `docs/FABRO.md`, on how to run the two workflows and what each proves.

Out of scope: the clarify, spec, design and build workflows, the intentable bridge, sandbox previews of the site, GitHub App setup, and a sandbox image that can run the Django test suite. Each gets its own change once this one shows the approach works. If the `claude-max` run cannot be made to work on Fabro, the plan's fallback is Cloudflare, as Nate said; that decision is his.

## Capabilities

### New Capabilities

- `fabro-runs`: how Fabro workflows in this repo are configured: which repository they target, where they run, how Claude Code authenticates, and what the two smoke-test workflows contain.

### Modified Capabilities

(none)

## Impact

- New files: `.fabro/project.toml`, `.fabro/daytona.Dockerfile`, `.fabro/workflows/hello/`, `.fabro/workflows/claude-max/`, `core/tests/test_fabro_config.py` and `docs/FABRO.md`.
- No change to the Django site, its data, its migrations or its deployment.
- Outside the repo:
  - The local Fabro server, upgraded to 0.400.0-nightly.0, a nightly build. Its secrets file was converted to the new format during the upgrade (see design.md).
  - A `CLAUDE_CODE_OAUTH_TOKEN` secret in its vault, and a replaced or removed `GITHUB_TOKEN`.
  - Daytona usage billed to Nate's account; Claude Code usage counted against the Max plan's limits.
  - One earlier `hello` run used Nate's OpenAI key (a few thousand tokens); later runs use no model.
