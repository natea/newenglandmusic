## Why

On 18 November 2026 Nate asked that a change's preview, made when its pull request opens, "point to the URLs on the site where the change can be observed or tested". The build agent knows which pages it changed, and what a reviewer should look at on each. Intentable's bridge (`add-delivery-board`) already reads an optional `preview` list in the build's result and links each page inside the preview when it posts the preview's address. This change has the build workflow write that list.

## What Changes

- **The agent names the pages to check.** `apply.md`'s record (`.intentable/build.json`) gains an optional `preview`: up to 8 `{"path": "/discover/", "check": "the Start button over the thumbnail"}` entries. Each is a path on the site from its root, with what a reviewer should look at there, written for someone who isn't a developer. `refactor.md` keeps the list true if refactoring moves a page.
- **The finish step checks and passes it on.** It fails the run on a malformed list: not a list, more than 8 entries, a path that isn't a plain site path, or a description that is empty or over 120 characters. Otherwise it copies the list into `.intentable/result.json` as `preview`.
- **A build that names no pages is fine.** The bridge then posts only the preview's address.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `issue-builds`: the agent's record may carry `preview`, checked by the finish step, and the result carries it to the bridge.

## Impact

- `.fabro/workflows/build/apply.md`, `refactor.md` and `workflow.fabro` (the finish step);
- the tests that read the build workflow (`core/tests/test_issue_builds.py`);
- `.fabro/workflows/build/README.md`, if it describes the record.

It works with `add-cloud-run-previews`, and shows nothing until that is built: intentable's bridge (`add-delivery-board`, deployed 18 November 2026) already reads the field.

**G2:** Nate confirmed the proposal on 18 November 2026 ("g2 on the add-preview-paths").
