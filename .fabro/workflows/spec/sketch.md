You are sketching screens for an OpenSpec proposal on the New England Music Project website, a Django app listing music venues, shows and acts. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`, and its folder is `openspec/changes/<change>/`.

Use the `html-wireframe` skill, unattended: nobody will answer a question or pick an option while you work. These are low-fidelity wireframes. They settle what goes on the screen and in what order, not how it looks. Where the skill's defaults differ from the rules below, the rules below win.

Read the proposal and design first. For the site's audience, vocabulary and content, read `PRODUCT.md`, the "Audience, job and content" section of the page's file in `.impeccable/surfaces/` where there is one (not every page has a file, and not every file has that section; read nothing else in those files), and the templates the change touches. Use real labels and representative content from the site, not lorem ipsum.

## Three options, one per file

Make three options that differ in structure: grouping, order, navigation, density, or where the main action sits. Colour is not a difference. Write each one to its own static file in `openspec/changes/<change>/sketches/`: `a.html`, `b.html` and `c.html`. Do not put the options in one file with a selector, and add no click-through: no `:target` panels inside these three files.

Keep them unfinished on purpose:
- a grayscale palette, system fonts only (`font-family: system-ui, sans-serif` and the like), plain borders, limited radius;
- labelled placeholders for images, maps and media: a grey box saying what goes there;
- no brand colours, gradients, shadows, illustrations or images. Do not generate images.

Lay each option out at 1440×900, the size of its thumbnail, and make it reflow at 390px wide with a `@media` rule. Style by class, not by id.

## Rules every sketch must follow

A later step checks each file, and the run fails if one breaks these rules:
- A self-contained HTML file with all styling in an inline `<style>` element or `style` attributes.
- No scripts, no event handlers, no forms, no iframes, no SVG, no HTML comments, and nothing loaded from another address: no web fonts, no outside stylesheets or images. An image, if you need one, is a `data:image/` URL. Links are `#` fragments only. No backslash escapes in CSS.
- No `<meta>` but `<meta charset="utf-8">` and `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Only these elements: `html`, `head`, `body`, `title`, `style`, `meta`, `main`, `header`, `footer`, `nav`, `section`, `article`, `aside`, `div`, `span`, `p`, `h1` to `h6`, `ul`, `ol`, `li`, `dl`, `dt`, `dd`, `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`, `caption`, `colgroup`, `col`, `a`, `img`, `figure`, `figcaption`, `strong`, `em`, `b`, `i`, `u`, `s`, `small`, `mark`, `code`, `pre`, `blockquote`, `br`, `hr`, `time`, `abbr`, `sup`, `sub`, `button`, `label`.
- Only these attributes: `class`, `id`, `style`, `title`, `lang`, `dir`, `role`, `alt`, `width`, `height`, `colspan`, `rowspan`, `scope`, `span`, `datetime`, `type`, `charset`, `name`, `content`, `href`, `src`.

So these are refused, though the skill may suggest them: `label for=`, `tabindex`, `hidden`, `disabled`, `placeholder`, `address`, `fieldset` and `legend`, `details` and `summary`, `textarea`, `kbd`, `input` and `select`. Draw a text field, a select or a checkbox as a labelled box. The sandbox has no browser, so check each file by reading it instead of opening it.

## options.json

Write `options.json` in the same folder: a list with one object per option, `{"file": "a.html", "label": "…", "thesis": "…", "risk": "…"}`. `label` is the option's short name, `thesis` is why this structure might suit the people who use the page, and `risk` is its tradeoff. People read these in the issue comment, so write them in plain words.

## The comparison page

When the three files are done, write `compare.html` in the same folder: one page that switches between the three options, under the same rules.
- At the top, a bar of three links, `#a`, `#b` and `#c`, each labelled with its option's `label`.
- Below it, a container with class `options` holding three panels with class `option` and the ids `a`, `b` and `c`.
- Show the targeted panel and hide the others: `.option { display: none; } .option:target { display: block; } .options:not(:has(:target)) #a { display: block; }`, so the page opens on A.
- Copy each option into its panel unchanged but for three adjustments: prefix its style rules with the panel's id (`#b .results { … }`), and turn rules for `html`, `body` or `:root` into rules on the panel itself (`#b { … }`); turn its links into `<span>` text styled like a link; and drop its ids. The only ids on the page are `a`, `b` and `c`, each once, and the only links are the three in the bar. Any other link would break the switching.

## design.md

Add a "Sketches" section to the change's `design.md` that links `sketches/a.html`, `sketches/b.html`, `sketches/c.html` and `sketches/compare.html`, and gives each option's label, thesis and risk.

Change nothing else: no other file in the change, no code, nothing under `.intentable/`.
