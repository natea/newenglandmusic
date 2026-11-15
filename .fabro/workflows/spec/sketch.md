You are sketching screens for an OpenSpec proposal on the New England Music Project website, a Django app listing music venues, shows and acts. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`, and its folder is `openspec/changes/<change>/`.

Read the proposal and design first, then the templates and CSS the change touches. Impeccable's design context is in `PRODUCT.md`, `DESIGN.md` and `.impeccable/`.

Use the Impeccable skill's decision step, unattended: nobody will answer a question or pick an option while you work. Make three distinct options for the screens the proposal needs. Do not generate images.

Write them into `openspec/changes/<change>/sketches/`:

- `a.html`, `b.html` and `c.html`: one self-contained HTML file per option, laid out at 1440×900, with all styling in an inline `<style>` element or `style` attributes. Use only these elements: `html`, `head`, `body`, `title`, `style`, `meta`, `main`, `header`, `footer`, `nav`, `section`, `article`, `aside`, `div`, `span`, `p`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `ul`, `ol`, `li`, `dl`, `dt`, `dd`, `table`, `thead`, `tbody`, `tfoot`, `tr`, `th`, `td`, `caption`, `colgroup`, `col`, `a`, `img`, `figure`, `figcaption`, `strong`, `em`, `b`, `i`, `u`, `s`, `small`, `mark`, `code`, `pre`, `blockquote`, `br`, `hr`, `time`, `abbr`, `sup`, `sub`, `button`, `label`, `kbd`, `samp`, `var`, `q`, `cite`, `dfn`, `del`, `ins`, `wbr`, `address`. Use system fonts only (`font-family: system-ui, sans-serif` and the like). No scripts, no event handlers, no forms, no iframes, no SVG, no HTML comments, no `<meta>` but `charset="utf-8"`, and nothing loaded from another address: no web fonts, no outside stylesheets or images. An image, if you need one, is a `data:image/` URL. Links are `#` fragments only.
- `options.json`: a list with one object per option, `{"file": "a.html", "label": "…", "thesis": "…", "risk": "…"}`.

Then add a "Sketches" section to the change's `design.md` that links `sketches/a.html`, `sketches/b.html` and `sketches/c.html` and gives each option's label, thesis and risk.

Change nothing else: no other file in the change, no code, nothing under `.intentable/`. A later step checks the sketches, and the run fails if one breaks these rules.
