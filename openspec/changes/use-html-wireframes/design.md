## Context

The `spec` workflow (from `add-spec-workflow`, merged on the fork's `main` but not archived) has a `sketch` agent on the `needs-design` route. Today `install` clones Impeccable at tag `skill-v4.8.0` and installs it as a Claude Code plugin, and `sketch.md` tells the agent to run Impeccable's decision step unattended, reading `PRODUCT.md`, `DESIGN.md` and `.impeccable/`.

Everything after the sketch step depends only on the files it writes, and it works per file:
- `bin/check-intentable-result spec --sketches` requires `a.html`, `b.html`, `c.html` and an `options.json` entry for each, that `design.md` links them, and that each sketch passes the HTML allowlist. The allowlist (`SAFE_ELEMENTS`, `SAFE_ATTRIBUTES`) has static elements, `button` and `label`, and no `form`, `input`, `select`, `textarea`, `fieldset`, `details`, `address`, `script`, `svg` or `iframe`. It has no `for`, `tabindex`, `hidden`, `disabled` or `placeholder` attribute. It refuses any backslash in CSS. `check_sketches` fails the whole run on the first refusal.
- The `thumbnails` job in `.github/workflows/spek.yml` takes one Chrome screenshot of each sketch file at 1440×900, half scale.
- The bridge's draft comment (`bridge/src/drafts.ts` in intentable) finds `sketches/[a-z].html`, shows a link and a thumbnail for each, with `label`, `thesis` (shown as "Why") and `risk` from `options.json`, and asks for a reply of a, b or c (Nate's request, 2 November 2026).
- `revise.md` edits sketches when a finding is about one.

effective-html (`plannotator/effective-html`, MIT) is a Claude Code plugin with eight skills. It has no release tags. Its `html-wireframe` folder has `SKILL.md` and Codex metadata (`agents/openai.yaml`). The skill, by default:
- puts two or three directions in one HTML file with a keyboard selector;
- uses semantic landmarks, forms, buttons and native controls;
- uses a grayscale palette, system type, plain borders and labelled placeholders;
- adds click-through behaviour where it helps a review;
- opens the result at desktop and mobile widths to check it;
- reads the `design-artifact` skill "when available", and links an outside docs page.

The skill puts "the user's explicit instructions" first in its order of authority, so a prompt can override its defaults.

## Goals / Non-Goals

**Goals:**
- Sketches at G2 that show structure, content and order, not a finished look.
- What the sketch step hands on stays the same, with one file added: the same three files, checks, thumbnails and comment, plus the comparison page.
- The skill pinned, so a run uses the version that was reviewed.

**Non-Goals:**
- Clickable sketches. `add-spec-workflow` left "Should sketches really be clickable?" for Nate: CSS-only `:target` panels pass today's checker and worked under the published policy on 3 November 2026; scripts don't pass. This change keeps sketches static and leaves that question open.
- The build stage that uses Impeccable on the picked sketch.
- Changing the checker's allowlist (the comparison page needs only new required-file checks).
- Linking the comparison page from the bridge's issue comment, which is intentable's.

## Decisions

**Three static files, not one file with a picker.** The skill's default is one file with a selector. We keep three files because everything downstream is per file: the checker requires `a.html`, `b.html` and `c.html`; `options.json` is keyed by `file`; the thumbnails job makes one image per file, so a picker file would give one thumbnail showing only its first direction; and the bridge's comment shows one thumbnail per file and asks for a, b or c. The skill's selector uses script or form controls, which the checker refuses.
- Alternative: one file with a CSS `:target` picker (`#a`, `#b`, `#c` links), which would pass the checker. It would mean changing the checker's required files, `options.json`, the thumbnails job (a screenshot per fragment), the bridge's comment and the spec's scenarios, and deciding how the a, b or c reply maps onto it.
- Alternative, taken alongside the three files: a fourth comparison page that switches between them with `:target` (Nate's choice, 9 November 2026). See the next decision.

**A comparison page beside the three files** (Nate's choice, 9 November 2026). The sketch agent also writes `sketches/compare.html`: one page with a panel for each option, `id="a"`, `id="b"` and `id="c"`, and a bar of `#a`, `#b` and `#c` links at the top, each labelled with the option's `label`. CSS shows the targeted panel (`.option:target`) and shows `a` when nothing is targeted (`.options:not(:has(:target)) #a`), so the page opens on A and the back button steps through the views. Each panel holds that option's screen as in its own file, with three adjustments:
  - its styles are prefixed by the panel's id so the three don't collide, and page-level rules (`html`, `body`, `:root`) become rules on the panel itself (`#a { … }`);
  - its links become plain text (a `<span>` styled like a link). Every link in a sketch is a `#` fragment, and on this page any fragment but `#a`, `#b` or `#c` would clear the panel's target: `href="#"` would jump back to A, and a link to an id inside a panel would leave no panel targeted and blank the page;
  - its own ids are dropped, so the only ids on the page are `a`, `b` and `c`, each once. So that no style is lost with them, the prompt asks for `a.html`, `b.html` and `c.html` to be styled by class, not by id. No script is needed, and the existing allowlist accepts it: `:target` and `:has` are plain CSS, and the links are fragments.
- **Written by the agent, not generated.** A script could only build it by merging three pages' styles, which means rewriting CSS selectors safely; the agent can write it with the styles already scoped. The cost is that a panel can drift from its file. → The prompt says to write `a.html`, `b.html` and `c.html` first and copy each into its panel unchanged but for the adjustments above, and revise is told to keep `compare.html` in step when it edits a sketch. The reviewers and Nate see both.
- **Checked like the others, and required.** `--sketches` requires `compare.html`, and requires `design.md` to link it. In `compare.html` it requires the ids `a`, `b` and `c`, each exactly once, and no other id, and links to each of `#a`, `#b` and `#c` and to nothing else. That catches a missing panel even when a copied sketch used one of those ids, and it catches the stray links that would break the switching. Whether the page opens on A is checked only in the live check, since it is a matter of CSS. The safety check already covers every `.html` in `sketches/`.
- **Published, not in the comment yet.** `publish-spek-page` already publishes every safe `.html` in `sketches/` and makes a thumbnail of each, so `compare.html` is published beside the others with one thumbnail of its default view. The bridge's comment matches only single-letter files (`sketches/[a-z].html`), so it ignores `compare.html` and keeps one column per option and the a, b or c reply. Linking the comparison page from the comment is a change to intentable's bridge, left for later; until then it is linked from the change's design, so it is one click from the Spek page.
- **Not clickable sketches.** The panels switch between options; inside each panel the option is as static as its file. Whether the options themselves should be clickable stays an open question.

**Copy the one skill from a pinned commit, don't install the plugin.** `install` runs:

```
git init --quiet /tmp/effective-html
git -C /tmp/effective-html fetch --quiet --depth 1 https://github.com/plannotator/effective-html <commit>
git -C /tmp/effective-html checkout --quiet FETCH_HEAD
mkdir -p ~/.claude/skills
cp -R /tmp/effective-html/skills/html-wireframe ~/.claude/skills/
```

`<commit>` is a full 40-character SHA, picked when this change is applied and recorded in the design then (the clone read for this proposal was at `5ce160a3e76dc1c0f9301f8a1903704ec607636a`, 31 October 2026). The current spec has the sketch skill pinned, and installing the plugin wouldn't be: the repository's `marketplace.json` gives the plugin's source as the GitHub URL itself with no ref, so Claude Code would fetch the default branch whatever was cloned. A user skill also keeps the skill out of the checkout, so it is never among the files the run changed (the bridge commits only the change's folder, but a stray skill folder would still be noise in Fabro's record).
- Alternative: vendor the skill into this repository. Rejected: it's a third-party file to keep in step by hand.
- Taken without Nate, about four in five likely to be his choice: copying the skill rather than installing the plugin follows from keeping it pinned.

**Consent to install effective-html.** Nate's 7 November choice is consent to use the skill in the sandbox; this change installs it nowhere else, and nothing runs it before his G4 and the live check he starts (tasks 3.1 and 4.1). `tot` isn't installed and nothing is published to tot.page.

**Only `html-wireframe`.** `design-artifact` is optional for the wireframe skill and is mostly about editorial polish, which the wireframe contract avoids. `html` (the router) and `html-prototype` aren't wanted at this stage. Open question for Nate below.

**The prompt overrides the skill's defaults.** `sketch.md`:
- names the `html-wireframe` skill and says to use it unattended: nobody answers questions while it works. The skill only runs when it is named;
- asks for three structurally different directions, one per static file (`a.html`, `b.html`, `c.html`), not one file with a selector, and no `:target` panels or click-through inside them. The skill wants two or three; three is our contract. Then it asks for `compare.html` as described above, the one place `:target` is used;
- keeps every existing rule the checker enforces: inline `<style>` only, system fonts, no scripts or event handlers, no forms or iframes, no SVG, no comments, nothing loaded from another address, `#` links only;
- lists the elements and attributes the checker allows, and names the likely refusals the skill would otherwise reach for: `label for=`, `tabindex`, `hidden`, `disabled`, `placeholder`, `address`, `fieldset` and `legend`, `details` and `summary`, `textarea`, `kbd`, and backslash escapes in CSS;
- says to draw a text field, select or checkbox as a labelled box, since `input` and `select` are refused;
- adds what the skill means by low fidelity: grayscale, plain borders, limited radius, labelled placeholders for images and maps, real labels and content from the site, no brand colours, gradients, shadows or images;
- lays each option out at 1440×900, the thumbnail's size, and reflows it at 390px wide with a `@media` rule. It allows `<meta name="viewport" content="width=device-width, initial-scale=1">`, which the checker already accepts, so the reflow shows on a phone;
- skips the skill's step of opening the result in a browser, since the sandbox has none, and asks for a check by reading the file instead;
- maps the skill's "short descriptive name and one sentence about its tradeoff" onto `options.json`: `label` is the name, `thesis` is why this structure might suit the people who use the page (the comment shows it as "Why"), `risk` is its tradeoff;
- points the agent at `PRODUCT.md`, the "Audience, job and content" section of the `.impeccable/surfaces/*.md` file for the page, where there is one (the venue surface and any new page have none, so the agent relies on `PRODUCT.md` and the templates), and the templates the change touches, and tells it to leave the rest of `.impeccable/surfaces/` alone. It doesn't name `DESIGN.md`, `.impeccable/design.json` or `.impeccable/mocks/`. Nate committed `.impeccable/` on 2 November 2026 because the files "are useful for making new sketches". The audience and content sections still are; the visual system isn't, for a wireframe.

The existing phrases the prompt test checks ("system fonts only", "No scripts", "nothing loaded from another address", "`options.json`", "Do not generate images") stay.

**Revise keeps the wireframes plain.** This follows from Nate's 7 November choice rather than being a decision of his own. `revise.md` gains one line: a sketch it edits stays a grayscale wireframe under the same rules, and its panel in `compare.html` changes with it, so a finding that a sketch is off-brand is answered in the summary, not by adding colour. It also allows the viewport `<meta>`, like `sketch.md`.

**Impeccable leaves `install`.** Its clone and `claude plugin install` go. The `.impeccable/` files, `PRODUCT.md` and `DESIGN.md` stay committed: `add-venue-pages` builds from `.impeccable/mocks/`, and the later build stage will use them.

**Archive order.** The `issue-proposals` spec exists only in `add-spec-workflow`'s change folder, so this change's MODIFIED requirement has nothing to merge into until that change is archived (`openspec validate` says so). `add-spec-workflow` is held open by task 5.3, which checks the thumbnails and their timing on the next real sketch run. This change's live check is such a run, so it closes 5.3 too. The order is: apply this change; run the live check; tick `add-spec-workflow` 5.3; archive `add-spec-workflow`; then archive this change. The order for intentable's own changes (host-on-spark, then add-spec-runs) is a separate repository's and doesn't hold this up.
- Alternative: write this change's spec as edits inside `add-spec-workflow`'s folder. Rejected: it would rewrite a merged, reviewed change's record of what Nate decided on 2 November.

**Tests.** The configuration tests read `workflow.fabro`, `sketch.md` and `revise.md` as text. They don't fetch effective-html or start Claude Code; GitHub, Fabro and the skill aren't touched. The live check is the only test that runs the skill.

## Risks / Trade-offs

- **The agent may not load a user skill through ACP.** The Impeccable plugin, installed in the same user's `~/.claude`, loaded on issue #9's run, so the adapter reads the user's settings, but a plain skill folder is a different path. → The live check looks in the sketch stage's output for the skill being invoked or its `SKILL.md` being read, not just its name, which the prompt gives anyway. If it doesn't load, the fallback is to put the skill's text into the prompt. A later bump of Claude Code or the adapter could stop loading it without any test noticing; the next sketch run's output is where that shows.
- **The skill pulls towards markup the checker refuses.** One refused tag fails the run and loses the proposal. → The prompt lists what's allowed and names the likely refusals; `check_sketches` still catches anything else before any reviewer starts.
- **Grayscale isn't checked by a machine.** The checker enforces safety, not style. → Reviewers and Nate see the sketches at G2, revise is told to keep them plain, and the prompt test checks that the prompt asks for grayscale.
- **Every spec run depends on the fetch.** `install` runs on every spec run, not only for `needs-design`, as Impeccable's clone did. A bare commit on a tagless repository is a weaker anchor than a tag: if the commit stopped being fetchable, every spec run would fail at `install`. → Bumping the pin is a one-line change. Fetching only on the sketch route is possible if that ever happens.
- **The skill reaches outside.** `SKILL.md` links `../design-artifact/SKILL.md`, which isn't copied, and an outside docs page; the sandbox has network access. → Harmless: neither changes the files the step writes, and the checker reads those.
- **The comparison page can drift from the three files.** → See the decision above; the checker checks its shape, not that each panel matches its file.
- **One more thumbnail.** The thumbnails job renders every `.html` in `sketches/`, so `compare.html` gets one too, showing panel A, which nothing reads yet. → One more Chrome render; task 4.2 times the job.
- **Fewer controls to sketch with.** Without `input` or `select`, a search form is a drawn box. → Acceptable for low fidelity.

## Open Questions

- **Should sketches be clickable?** Still Nate's question from `add-spec-workflow`. The prompt keeps them static until he decides.
- **Should `design-artifact` be copied too?** The wireframe skill reads it when it is there, for composition and hierarchy. I'd leave it out to keep the sketches plain, but it's Nate's call.
