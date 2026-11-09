## Context

The `spec` workflow (from `add-spec-workflow`, merged on the fork's `main` but not archived) has a `sketch` agent on the `needs-design` route. Today `install` clones Impeccable at tag `skill-v4.8.0` and installs it as a Claude Code plugin, and `sketch.md` tells the agent to run Impeccable's decision step unattended, reading `PRODUCT.md`, `DESIGN.md` and `.impeccable/`.

Everything after the sketch step depends only on the files it writes, not on the skill that wrote them:
- `bin/check-intentable-result spec --sketches` checks that `a.html`, `b.html`, `c.html` and `options.json` exist, that `design.md` links them, and that each sketch passes the HTML allowlist. The allowlist has static elements, `button` and `label`, but no `form`, `input`, `select`, `script`, `svg` or `iframe`.
- The `thumbnails` job in `.github/workflows/spek.yml` renders each sketch with Chrome at 1440×900 and half scale.
- The bridge's comment shows each option's label, thesis and risk from `options.json`.

effective-html (`plannotator/effective-html`, MIT) is a Claude Code plugin with eight skills. It has no release tags. Its `html-wireframe` skill is one file, `SKILL.md`, which by default:
- puts two or three directions in one HTML file with a keyboard selector;
- uses a grayscale palette, system type, plain borders and labelled placeholders;
- adds click-through behaviour where it helps a review;
- opens the result at desktop and mobile widths to check it;
- reads the `design-artifact` skill "when available".

The skill puts "the user's explicit instructions" first in its order of authority, so a prompt can override its defaults.

## Goals / Non-Goals

**Goals:**
- Sketches at G2 that show structure, content and order, not a finished look.
- No change to what the sketch step hands on: same files, same checks, same thumbnails and comment.
- The skill pinned, so a run uses the version that was reviewed.

**Non-Goals:**
- Clickable wireframes. They need scripts, which the checker refuses and the publishing policy rules out.
- The build stage that uses Impeccable on the picked sketch.
- Changing the checker's allowlist.

## Decisions

**Copy the one skill from a pinned commit, don't install the plugin.** `install` runs:

```
git init --quiet /tmp/effective-html
git -C /tmp/effective-html fetch --quiet --depth 1 https://github.com/plannotator/effective-html <commit>
git -C /tmp/effective-html checkout --quiet FETCH_HEAD
mkdir -p ~/.claude/skills
cp -R /tmp/effective-html/skills/html-wireframe ~/.claude/skills/
```

`<commit>` is a full 40-character SHA, picked when this change is applied and recorded in the design then (the clone read for this proposal was at `5ce160a3e76dc1c0f9301f8a1903704ec607636a`, 31 October 2026). Installing the plugin wouldn't be pinned: the repository's `marketplace.json` gives the plugin's source as the GitHub URL itself, so Claude Code would fetch the default branch whatever was cloned. A user skill also keeps the skill out of the checkout. A project skill under `.claude/skills/` would be a file the run changed, and the draft check refuses changes outside the change's folder.
- Alternative: vendor the skill into this repository. Rejected: it's a third-party file to keep in step by hand, and it would sit in the sandbox's checkout like any other file the agents read.
- Taken without Nate, about four in five likely to be his choice: copying the skill rather than installing the plugin follows from pinning, which he asked for.

**Only `html-wireframe`.** `design-artifact` is optional for the wireframe skill and is mostly about editorial polish, which the wireframe contract avoids. `html` (the router) and `html-prototype` aren't wanted at this stage. Open question for Nate below.

**The prompt overrides the skill's defaults.** `sketch.md`:
- names the `html-wireframe` skill and says to use it unattended: nobody answers questions while it works;
- asks for three structurally different directions, one per file (`a.html`, `b.html`, `c.html`), not one file with a selector. The skill wants two or three; three is our contract;
- keeps every existing rule the checker enforces: inline `<style>` only, system fonts, no scripts or event handlers, no forms or iframes, no SVG, no comments, nothing loaded from another address, `#` links only;
- adds what the skill means by low fidelity: grayscale, plain borders, limited radius, labelled placeholders for images and maps, real labels and content from the site, no brand colours, gradients, shadows or images;
- says to draw a text field, select or checkbox as a labelled box, since `input` and `select` are refused;
- lays each option out at 1440×900, the thumbnail's size, and asks it to reflow at 390px wide with a `@media` rule, which the checker allows. The skill asks for both widths;
- skips the skill's step of opening the result in a browser, since the sandbox has none, and asks for a check by reading the file instead;
- maps the skill's "short descriptive name and one sentence about its tradeoff" onto `options.json`: `label` is the name, `thesis` is the structural decision the option makes, `risk` is its tradeoff;
- points the agent at `PRODUCT.md` and the templates the change touches, for vocabulary and content, and not at `DESIGN.md` or `.impeccable/`, which carry the visual system the wireframe should leave out.

The existing phrases the prompt test checks ("system fonts only", "No scripts", "nothing loaded from another address", "`options.json`", "Do not generate images") stay.

**Impeccable leaves `install`.** Its clone and `claude plugin install` go. The `.impeccable/` files, `PRODUCT.md` and `DESIGN.md` stay committed: `add-venue-pages` builds from `.impeccable/mocks/`, and the later build stage will use them.

**Archive order.** The `issue-proposals` spec exists only in `add-spec-workflow`'s change folder, so this change's MODIFIED requirement has nothing to merge into until that change is archived (`openspec validate` says so). `add-spec-workflow` is held open by task 5.3, which checks the thumbnails on the next real sketch run. This change's live check (task 4.2) is a real sketch run, so it closes 5.3 too. The order is: apply this change; run the live check; tick `add-spec-workflow` 5.3; archive `add-spec-workflow`; then archive this change. That keeps this change's delta written against the requirement as `add-spec-workflow` states it.
- Alternative: write this change's spec as edits inside `add-spec-workflow`'s folder. Rejected: it would rewrite a merged, reviewed change's record of what Nate decided on 2 November.

**Tests.** The configuration tests read `workflow.fabro` and `sketch.md` as text. They don't fetch effective-html or start Claude Code; GitHub, Fabro and the skill aren't touched. The live check is the only test that runs the skill.

## Risks / Trade-offs

- **The agent may not find a user skill through ACP.** The Impeccable plugin was installed in the same user's `~/.claude` and loaded, but a plain skill folder is a different path. → The live check confirms the agent's output names the skill. If it doesn't load, the fallback is to put the skill's text into the prompt.
- **The skill could pull the agent towards a selector or scripts.** → The prompt says so explicitly, and `check_sketches` fails the run before any reviewer starts if a sketch has a script.
- **Grayscale isn't checked by a machine.** The checker enforces safety, not style. → The reviewers and Nate see the sketches at G2, and the prompt test checks that the prompt asks for grayscale.
- **The pinned commit ages.** → Bumping it is a one-line change with a review of the skill's diff.
- **Fewer controls to sketch with.** Without `input` or `select`, a search form is a drawn box. → Acceptable for low fidelity; clickable prototypes are out of scope.

## Open Questions

- Should `design-artifact` be copied too? The wireframe skill reads it when it is there, for composition and hierarchy. I'd leave it out to keep the sketches plain, but it's Nate's call.
