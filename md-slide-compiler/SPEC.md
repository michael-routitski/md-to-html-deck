# Markdown-to-HTML Slide Compiler — Functional & Technical Specification

**Status:** Draft for approval (no implementation authorized)  
**Version:** 0.2  
**Decision baseline:** Q1–Q45, Rounds 1–5  
**Product goal:** Compile a Markdown presentation into one portable HTML file, with no AI, application server, Node.js, or build process needed at viewing time.

## 1. Scope and governing principles

The compiler is a deterministic, single-command Python application. Its input is one UTF-8 Markdown file containing YAML frontmatter; its output is one `.html` file beside that Markdown file. It uses a standards-based GitHub-Flavoured Markdown (GFM) parser, a separate internal Python module for code fences, and an HTML assembly/runtime module. The generated HTML embeds the resolved base-layout and theme stylesheets (either explicitly supplied by the deck or selected from compiler-bundled defaults) and all local Markdown images. Prism and Mermaid are loaded at **pinned versions from CDN** when needed. External HTTPS assets explicitly referenced by CSS may still require network access.

The output is **one file, but not fully offline**. Do not describe it as zero-dependency HTML. The compiler may use Python packages installed once; the compiled document must require no Python and no local asset directory to view, provided network dependencies are available.

**Non-goals:** exact Marp/Marpit implementation; arbitrary slide-layout DSL; per-slide CSS classes; arbitrary HTML authoring; PDF/print export; presenter view; server-side rendering; syntax validation of Mermaid using a separate engine; AI assistance at compile or view time; automatic text shrinking; a general-purpose browser UI framework.

The `.marpit` class, `<section>` structure, and pagination attributes are deliberate *compatibility-inspired conventions*, not a warranty that arbitrary official Marp themes or Marp directives will work. A theme MUST conform to this project's CSS contract.

## 2. Decision ledger and reconciliations

| Decisions | Binding outcome |
|---|---|
| Q1–Q7 | Marpit-inspired semantic slides; CDN-backed single file; one visible slide; local CSS; fixed widescreen 16:9; strict overflow (no content scrolling/shrinking). |
| Q8–Q17 | GFM; `---` slide delimiter; plain-text/Prism/Mermaid fence split; selective Prism loads; embedded JPEG/PNG/SVG/WebP/GIF; Markdown-relative images; global styles/directives; raw HTML forbidden; browser-console diagnostics. |
| Q18–Q26 | Browser/CSS-owned responsive geometry; *two* local CSS inputs; proportional automatic media fitting; minimal keyboard controls; no visible controls; `python compile.py deck.md`; collect diagnostics; pinned CDN versions; no print/PDF commitment. |
| Q27–Q35 | Both CSS paths supported in frontmatter, with generator-bundled fallback defaults when omitted; viewport/container-responsive typography; JS measures residual media space; preserve intrinsic aspect ratios; Marp-inspired directive names; compiler-resolved Prism dependency list; unknown language warning + plain text; reserved header/footer space; strict source validation. |
| Q36–Q45 | Independent proportional media fitting; static validation only; forbid local assets referenced by CSS; allow approved CDN resources and HTTPS CSS URLs; Marpit pagination attributes; byte-reproducible output; internal code module; overwrite on success; reject unlabelled fences; Mermaid configuration in YAML. |

**Reconciliations, now normative:**

1. **Strict source validation is not “reject every unfamiliar word”.** Fatal errors cover detectable unsupported structural constructs and invalid inputs. The explicit Q33 exception allows an unknown *labelled* code fence with a warning and plain-text output. An *unlabelled* fence is fatal (Q44).
2. **Browser-owned geometry is compatible with 16:9.** CSS maintains the aspect ratio and responsive typography. No fixed-pixel canvas with a JS `transform: scale(...)` is required.
3. **Automatic fitting applies only to images and Mermaid SVGs**, never to paragraphs/tables/code/text. If fixed-height text consumes all space, media may be reduced to a practical minimum and the slide may still overflow; issue console diagnostics. “Fit” is best effort, not a promise of legible diagrams in arbitrary content density.
4. **Both stylesheet slots exist for every deck, but frontmatter overrides are optional.** The compiler resolves each stylesheet independently: an explicit local path wins; an omitted key selects the corresponding default CSS in the compiler directory. This is the new default-behaviour amendment to Q27.
5. **No local assets inside CSS.** The compiler embeds local *Markdown* images, but it does not resolve local `url(...)` in CSS. HTTPS or `data:` CSS URLs are allowed and may need a network connection.
6. **Strict validation and safe overwrite are complementary.** Collect all detectable compiler diagnostics; on any fatal error, do not replace/create the output. On success, replace the output atomically. This elaborates Q24, Q35 and Q43.

## 3. Directory structures and application organization

### 3.1 Expected presentation input directory (prefer flat)

A presentation is defined by one Markdown file and, optionally, its own base-layout and visual-theme CSS files. Local images are resolved relative to the Markdown file. **A flat directory is preferred for small decks**, but is not mandatory:

```text
my-presentation/
├── presentation.md            # Required input document
├── base.css                   # Optional deck-specific layout override
├── theme.css                  # Optional deck-specific visual theme override
├── architecture.png           # Optional local media referenced from Markdown
├── screenshot.jpg             # Optional local media referenced from Markdown
└── diagram.svg                # Optional local media referenced from Markdown
```

For a larger deck, subdirectories are permitted and must not change the resolution rules:

```text
my-presentation/
├── presentation.md
├── styles/
│   ├── base.css
│   └── theme.css
└── media/
    ├── architecture.png
    └── screenshot.jpg
```

- `presentation.md` is the only mandatory input file in the presentation directory. The file must contain YAML frontmatter, but **neither `layout` nor `theme` is mandatory**.
- If `layout: ./base.css` and/or `theme: ./theme.css` are present, these refer to files **relative to the directory containing `presentation.md`**; paths do not resolve against the current working directory or compiler directory.
- Images referenced as `![Architecture](architecture.png)` or `![Architecture](media/architecture.png)` likewise resolve against the Markdown directory and are embedded in the resulting HTML.
- The output `presentation.html` is written alongside `presentation.md`, not inside the compiler installation directory.
- Unused `.css` and image files are not automatically included or discovered; references determine which files are loaded. Local image paths must also obey the directory-tree boundary in §8.
- The compiler does not require authors to copy bundled default CSS files into each presentation directory.

### 3.2 Generator script directory (approximately five program/support files)

The compiler installation holds the entry point, its internal modules, a dependency manifest and **two mandatory bundled default CSS stylesheets**:

```text
md-slide-compiler/
├── compile.py                 # Master CLI entry point and compilation orchestration
├── markdown_engine.py         # Frontmatter, slide parsing, semantic HTML, assets
├── code_fences.py             # Text/Prism/Mermaid fence dispatch and Prism registry
├── html_runtime.py            # HTML assembly, embedded runtime, pinned CDN references
├── requirements.txt           # Pinned Python dependencies
├── base.css                   # Built-in default 16:9 responsive slide layout
└── theme.css                  # Built-in default visual theme
```

Tests and fixtures may reside in additional files/directories, outside the approximate five-file program target. The CSS defaults are supporting assets, **not additional Python modules**, and are required for an install to be valid. The standalone compiler directory can be placed anywhere on disk; its defaults are resolved relative to the location of `compile.py` (resolved installation/script directory), **not the shell's current working directory and not the Markdown input directory**.

Default styles must comply with the CSS ownership contract in §10: `base.css` controls 16:9 geometry, viewport sizing, metadata reservation and media containment; `theme.css` controls typography, colours and semantic content appearance. Both default CSS files must be useful together without any deck-specific overrides. Neither may depend on local `url(...)` assets or CSS `@import` (see §8).

### 3.3 Per-stylesheet selection and fallback

Resolve each stylesheet **independently**, with the following deterministic precedence:

| Frontmatter key | Key present with valid local path | Key omitted | Key present but empty/null/invalid |
|---|---|---|---|
| `layout` | Use Markdown-relative CSS path | Use compiler's `base.css` | Fatal validation error; **do not** fall back |
| `theme` | Use Markdown-relative CSS path | Use compiler's `theme.css` | Fatal validation error; **do not** fall back |

Four valid combinations are therefore: both bundled defaults, explicit layout + default theme, default layout + explicit theme, or both explicit paths. A specified but missing/unreadable CSS file is a fatal error and must not be silently replaced with a default. Likewise, an omitted key whose bundled default CSS is missing/unreadable is a fatal compiler installation/configuration error.

Regardless of origin, resolved layout CSS is embedded first and resolved theme CSS second. Compilation remains independent of the user's current working directory, network and machine-specific absolute paths. The generated HTML must contain only the resolved CSS bytes (appropriately safely embedded), not the filesystem locations of the source stylesheets.

## 4. Command-line interface and files

Invocation:

```text
python compile.py <path-to-deck.md>
```

- Exactly one positional `.md` input path; no flags in v1. Display usage and return nonzero for missing/extra arguments.
- Input must exist, be a regular readable UTF-8 file (UTF-8 BOM may be accepted and stripped).
- Output is `<input-dir>/<input-stem>.html`; e.g. `docs/talk.md` → `docs/talk.html`, regardless of shell working directory.
- Explicit frontmatter CSS paths and Markdown image paths resolve relative to the Markdown directory. Omitted `layout`/`theme` paths resolve to bundled defaults in the compiler directory (§3.3). CSS local `url(...)` references remain **forbidden**.
- Read all inputs and collect static diagnostics before committing output. Emit concise diagnostics as `path:line:column: ERROR|WARNING [CODE] message` when a source position is available; otherwise use `path: ERROR|WARNING [CODE] message`.
- Fatal diagnostic(s): exit 1, leave any existing output unchanged, remove temporary output. Argument/IO failure: exit 2. No fatal errors: exit 0 even if there are warnings.
- On success, atomically replace an existing output in the same directory, using a temporary file and filesystem replacement. Do not include build time, random keys, absolute machine paths or environment-dependent identifiers.
- UTF-8 output, consistent `\n` line endings, deterministic HTML order, deterministic asset encoding, deterministic script ordering and no network fetch at compilation (all CSS themes must be local).

## 5. Required YAML frontmatter

Frontmatter is mandatory, begins at byte 0 (after an optional UTF-8 BOM), opens with a line consisting of `---` and ends at the next standalone `---`. After that closing line, every standalone `---` is a slide separator (except when inside fenced code). YAML must be a mapping with unique keys. Unknown keys are fatal in v1, rather than silently ignored.

### 5.1 Schema

| Key | Type | Required | Default / semantics |
|---|---|---:|---|
| `layout` | nonempty string, if present | No | Omitted: compiler-bundled `base.css`; otherwise a local Markdown-relative CSS path. Compiler extension, not a standard Marp key. |
| `theme` | nonempty string, if present | No | Omitted: compiler-bundled `theme.css`; otherwise a local Markdown-relative CSS path. No theme identifiers or URLs. |
| `header` | string | No | Absent/empty means no `<header>`. Text only, HTML-escaped. |
| `footer` | string | No | Absent/empty means no `<footer>`. Text only, HTML-escaped. |
| `paginate` | boolean | No | `false`. Boolean must be YAML boolean, not quoted string. |
| `mermaid` | mapping | No | Explicit limited Mermaid config; see below. |

Example with explicit overrides (both may also be omitted to use defaults):

```yaml
---
layout: ./styles/base.css
theme: ./styles/technical.css
paginate: true
header: "Trading Platform"
footer: "Engineering"
mermaid:
  theme: neutral
---
```

### 5.2 Mermaid configuration

Allow `mermaid.theme` with values `default`, `dark`, `forest`, `neutral`, or `base`. Default `default`. In v1, no arbitrary object injection, custom JavaScript, `themeVariables`, security-level overrides, inline Mermaid `%%{init: ...}%%` directives, or per-diagram theme settings. Reject unsupported config keys/values rather than guessing. Always enforce Mermaid `securityLevel: 'strict'`. Do not assume arbitrary CSS themes can recolour Mermaid internals; Mermaid theme selection is independent of CSS.

**Note:** The restriction of Mermaid's own initialization directives is a project-specific security/simplicity rule; it should be enforced or flagged when the input block contains those directives.

## 6. Markdown contract

- Parse GFM: ATX/Setext headings, paragraphs, emphasis, strong, strikethrough, links, inline code, blockquotes, ordered/unordered/nested lists, GFM tables, task lists, images, and fenced code; preserve normal semantic nesting.
- A line containing exactly `---`, optionally surrounded by horizontal whitespace, separates slides **outside the opening frontmatter and fenced code**. It is not rendered as `<hr>`. The horizontal-rule forms `***` and `___` do **not** separate slides; they remain normal horizontal rules. Note: this is a deliberate deviation from generic Markdown parsing.
- Slide boundaries must be determined token-aware, not by blind string replacement. A horizontal-rule-looking line in a fenced block, or otherwise part of protected Markdown syntax, is not a separator. A bare `---` line can no longer be used for a literal horizontal rule in slide content; use `***` instead.
- Reject empty presentations (no non-whitespace content). Deliberately empty slides are permitted only between two nonempty slide segments? **No:** in v1, leading, adjacent, or trailing slide separators yielding an empty slide are fatal; this prevents accidental blank slides.
- Treat standard inline HTML, raw HTML blocks, embedded `<script>`, `<style>`, `iframe`, and HTML comments with special Marpit directives as unsupported. Generic HTML comments may be silently discarded as previously agreed, but MUST never be executed or interpreted as slide directives. Explicit Marpit `_class`, `_backgroundColor`, or similar comment directives are fatal unsupported syntax. All ordinary user text and attributes are HTML-escaped.
- Other Marp-specific extensions (background-image `![bg]`, split-background image modifiers, directives, speaker notes, CSS-scoped fragments) are unsupported. Recognised unsupported syntax should fail validation; do not treat bare words resembling directives as errors.
- Rendering source syntax such as `[link](https://example.org)` is allowed. Relative Markdown *links* (as distinct from images) are passed through as safe relative references, and may not function when a single HTML file is moved; a warning is preferable. Reject `javascript:` and other executable URL schemes.
- Task list checkboxes are rendered noninteractive (`disabled`) and do not create an application control.

### 6.1 Slide content element mapping

| Source construct | HTML |
|---|---|
| Slide | Direct `<section>` inside `.marpit` |
| Heading | `<h1>` ... `<h6>` |
| Paragraph | `<p>` |
| Lists | `<ul>` / `<ol>` with `<li>` and nested lists |
| Quote | `<blockquote>` |
| Inline code | `<code>` |
| GFM table | `<table><thead>...` / `<tbody>...` |
| Horizontal rule (`***`, `___`) | `<hr>` |
| Inline Markdown image | `<img src="data:..." alt="...">` |
| Text fence (`txt`, `text`, `plaintext`) | `<pre>escaped text</pre>` |
| Supported source language fence | `<pre class="language-x"><code class="language-x">escaped source</code></pre>` |
| Mermaid fence | `<pre class="mermaid">escaped raw Mermaid source</pre>` |

No custom typographic wrapper `<div>` is allowed around headings/paragraphs/lists. The `.marpit` wrapper is the sole sequence wrapper. An optional media-only wrapper is **not** necessary in v1; runtime identifies direct image/diagram nodes. No per-slide classes (Q14=A).

## 7. Code fences and Prism

Code fences require a nonempty language identifier. Recognize case-insensitive aliases, normalizing at least:

- `txt`, `text`, `plaintext` → plain `<pre>`.
- `mermaid` → dedicated Mermaid branch; never Prism.
- `cs`, `csharp` → `csharp`; `c++`, `cpp`, `cxx` → `cpp`; `js`, `javascript` → `javascript`; `py`, `python` → `python`; `sh`, `bash`, `shell` → `bash`.
- Additionally support at minimum `java`, `json`, `yaml`, `yml`, `sql`, `xml`, `html`, `css`, `typescript`, `ts`, and `powershell` with documented aliases and canonical grammar names. Use canonical Prism grammar identifiers, not arbitrary user text, when generating CSS classes and script URLs.
- A language identifier containing whitespace/extra info-string metadata is unsupported in v1 unless explicitly documented; fail rather than silently dropping options.
- An **unknown, nonempty** label is a warning (`W_UNKNOWN_CODE_LANGUAGE`) and falls back to escaped plain `<pre>`; an **absent** label is a fatal error (`E_MISSING_CODE_LANGUAGE`).
- HTML-escape code content (`&`, `<`, `>`) while preserving text and newlines. Never parse Markdown inside code fences.
- The compiler scans the Markdown, deduplicates required canonical languages, resolves Prism dependency order from a **version-matched, pinned component dependency manifest**, and emits only the scripts actually needed (plus Prism core). Unsupported/unknown languages do not trigger a grammar request.
- Code highlighting JS is used without an extra Prism stylesheet; the two authored stylesheets may style `pre[class*="language-"]`, `.token.keyword`, `.token.string`, etc. When no recognised source-code fence is present, emit no Prism runtime at all.
- Prism MUST NOT process `.mermaid` nodes; do not emit `language-mermaid` or `language-none` markup for Mermaid content.

### 7.1 CDN policy

Pinned defaults for the initial implementation contract: **PrismJS 1.29.0** and **Mermaid 12.0.0**, to be confirmed against the CDN in integration tests before first release. Pin exact patch versions in compiler constants and a test fixture; never reference `latest` or an unpinned major-only URL in generated output. CDN origin: `https://cdn.jsdelivr.net`. Conditional inclusion: Prism only for recognised source-code fences; Mermaid only if at least one Mermaid fence exists. Browser load errors must produce console diagnostics with actionable URLs.

The compiler makes **no** network request to fetch Prism or Mermaid at compile time. Library scripts are fetched by the browser when the HTML is opened. CSS `url(https://...)` requests may also occur at viewing time.

## 8. Images and other asset rules

- Markdown images must resolve to **existing local files**, relative to the Markdown source directory; absolute, traversal-outside-project, `file:`, `http:`, `https:`, and `javascript:` Markdown image URLs are outside the v1 contract and must be rejected. Path traversal within the deck directory is allowed if it resolves to an existing file; escaping that directory is rejected for portability/safety.
- Support extensions/signatures for JPEG (`image/jpeg`), PNG (`image/png`), SVG (`image/svg+xml`), WebP (`image/webp`), and GIF (`image/gif`). Validate type consistently rather than trusting extension alone. SVG should be treated as an image resource, not injected as inline HTML.
- Embed all local Markdown image assets as base64 Data URLs, e.g. `data:image/jpeg;base64,...`. Preserve original bytes; no recompression, optimization or lossy transformations. Encode each source deterministically.
- Markdown alt text is HTML-escaped and preserved. Any title attribute is escaped; width/height annotations are out of scope. SVG external references/scripts may not make SVG self-contained; validate/reject unsafe SVG constructs such as external resource references or scripts rather than assuming base64 embedding sanitizes them.
- Links to an image are allowed, but arbitrary remote image sources are not.
- CSS files are read and embedded literally as UTF-8 text after safety validation, with **no local asset rewriting**. Disallow `@import`, `url(./...)`, `url(../...)`, `url(/...)`, `url(file:...)` and unqualified local filenames in CSS. Accept `url(https://...)`, `url(data:...)`, and fragment-only URLs such as `url(#gradient)` when meaningful. Disallow `http:` resources. CSS must not contain executable embedded script or HTML-closing breakout sequences; safely encode or reject them before placing text inside `<style>`.
- A remote font referenced by CSS remains remote. If that host is unavailable, the browser may use fallback fonts; the compiled HTML remains intact.

## 9. HTML emission contract

Emit a complete `<!doctype html>`, `<html lang="en">`, `<head>` with UTF-8 and viewport metadata, two **ordered** embedded `<style>` elements (resolved `layout` first, then resolved `theme`), optional pinned CDN dependencies, `<body>`, and a single `<div class="marpit">` containing one `<section>` per slide. Avoid generated timestamps and unstable IDs.

**Normative shape (illustrative content; not implementation code):**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style id="slide-layout">/* exact contents of layout CSS */</style>
  <style id="slide-theme">/* exact contents of theme CSS */</style>
  <!-- conditional pinned Prism dependencies, in dependency order -->
</head>
<body>
  <div class="marpit">
    <section data-marpit-pagination="1" data-marpit-pagination-total="2">
      <header>Trading Platform</header>
      <h1>Example</h1>
      <p>Illustrative content</p>
      <footer>Engineering</footer>
    </section>
    <section data-marpit-pagination="2" data-marpit-pagination-total="2">
      <header>Trading Platform</header>
      <pre class="mermaid">flowchart LR
A--&gt;B</pre>
      <footer>Engineering</footer>
    </section>
  </div>
  <!-- deterministic inline navigation/fitting code; optional Mermaid module import -->
</body>
</html>
```

- **Header/footer** elements are direct section children, inserted *before/after* semantic content respectively only if configured and nonempty. They contain escaped plain text, not Markdown-rendered HTML.
- **Pagination:** if `paginate: true`, add `data-marpit-pagination="N"` and `data-marpit-pagination-total="T"` to each section. If `paginate: false`, omit both pagination attributes. `N` is 1-based and `T` is total slides. Theme draws pagination with `section[data-marpit-pagination]::after { content: attr(data-marpit-pagination); }`; the runtime adds no visible counter or controls.
- CSS IDs on the `<style>` tags are compiler-reserved; theme authors should not depend on modifying them.
- Browser runtime must not create extra wrapper `div`s around slide contents. It may set element styles and internal state attributes required for visibility/measurement; those state attributes are not part of the theme's public styling contract.
- If no Mermaid exists, do not reference Mermaid. If no Prism-required code exists, do not reference Prism. If neither exists, the deck's core navigation/runtime works without those CDNs (except remote CSS assets).

## 10. CSS layout/theme interface

### 10.1 Layout file — responsibility and invariants

The resolved `layout` CSS (explicit or bundled default) owns slide viewport positioning, 16:9 geometry, visible/hidden slide mechanics, content box sizing, reserved metadata areas and robust media containment. No JavaScript `transform: scale` of an absolute-pixel slide canvas. Use CSS aspect ratio and responsive dimensions so the visible slide is the largest 16:9 rectangle fitting the browser viewport, centered within it.

Minimum invariants:

- Exactly one section is visibly presented in on-screen mode; hidden slides cannot intercept pointer or keyboard interactions. The runtime must still be able to measure/layout hidden slides for Mermaid and media fitting (temporary measurement state is allowed).
- `.marpit` occupies the available viewport presentation stage. `section` uses `aspect-ratio:16/9` and stays fully within both viewport width and height. Content is clipped or flagged when outside bounds; do not scroll within a slide.
- Establish stable, reserved header/footer/pagination lanes via CSS variables (recommended names: `--slide-header-space`, `--slide-footer-space`, `--slide-padding-x`, `--slide-padding-y`). Their actual values are supplied by the resolved layout CSS (including the bundled default), **not** hidden compiler constants. Header/footer must not overlap the main content box under conforming CSS.
- The section is a CSS size-query container (or equivalent), allowing `cqw`/`cqh`-based typography. Browser support is defined for current evergreen Chromium/Firefox/Safari versions supporting modern container queries and ES modules.
- Media elements always preserve aspect ratio and can shrink into remaining content space, never crop/stretch; do not grow small assets beyond intended display dimensions unless the theme explicitly provides a natural-width convention.
- Pagination pseudo-element must be placed within the reserved metadata space, not over main content.

### 10.2 Theme file — responsibility and constraints

The resolved `theme` CSS (explicit or bundled default) owns colour, typography, margins, list/table/code styling, image/diagram aesthetics and header/footer/pagination appearance. Preferred selectors: `section`, `h1`–`h6`, `p`, `ul`, `ol`, `li`, `blockquote`, `table`, `th`, `td`, `pre`, `code`, `.token.*`, `img`, `pre.mermaid`, `.mermaid svg`, `header`, `footer`, and `section::after`.

**Do not** redefine geometry, slide visibility, viewport/root positioning or the runtime's fitting state. Stylesheets are embedded layout-first, theme-second; therefore this is a *documented contract*, not a CSS sandbox. Violations may cause browser overflow warnings, but compiler-side CSS semantic validation is intentionally limited.

Typography should use size-relative CSS units (`cqw`, `cqh`, `clamp()` where appropriate) so text scales naturally with the slide. A user theme that chooses fixed pixel font sizes is possible CSS but outside the recommended responsive contract. Do not insert element-specific generated font sizes into the HTML.

### 10.3 Containment and CSS specificity

- Use semantic selectors with low specificity. Avoid `!important` except where the layout must protect navigation/visibility invariants.
- The layout CSS reserves a rectangular body region after header/footer/padding. The runtime measures actual rendered positions and can assign media-specific max dimensions or CSS custom properties; it must not mutate theme typography.
- When `paginate: false`, the pagination pseudo-element must produce no text (including if a theme unconditionally defines `section::after`). Conforming themes should scope it to `[data-marpit-pagination]`.

## 11. Browser runtime contract

### 11.1 Navigation

Presentation starts at slide 1 on every page load (no hash deep-linking in v1). Only one slide is visible. Keyboard controls, when focus is not inside an editable element:

| Key | Action |
|---|---|
| `ArrowRight`, `PageDown`, `Space` | Next slide |
| `ArrowLeft`, `PageUp` | Previous slide |
| `Home` | First slide |
| `End` | Last slide |

Clamp at deck edges. Prevent default scrolling for captured keys. No on-screen counter, navigation buttons, mouse wheel navigation, click-to-advance, fullscreen shortcut, slide URL hashes, or presenter controls. Browser fullscreen may still be invoked through normal browser UI.

### 11.2 Load sequence and optional libraries

1. Parse the static HTML and apply authored layout/theme CSS.
2. Await `document.fonts.ready` when supported and wait for embedded image intrinsic sizes (`decode()`/load fallback).
3. If Mermaid blocks exist, import the **pinned** Mermaid ESM from jsDelivr. Call `mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: ... })`, then explicitly `await mermaid.run({ nodes: ... })`; this prevents uncontrolled double rendering and allows deterministic post-render measurement.
4. Prism scripts load only when required, with grammar dependencies ordered and highlighting invoked after Prism core/grammars are available. Prism must never target Mermaid blocks.
5. Measure content/media and fit each image/diagram; then test overflow. Recompute on viewport resize and font availability changes, debounced to avoid repeated layout thrashing.
6. Runtime errors are written to `console.error` and warnings to `console.warn`, including 1-based slide number and actionable context. No visible overlays, alerts, blocking dialogs or server callbacks.

Mermaid diagrams may render to SVG even when initially hidden; the runtime must ensure they are temporarily measurable under a non-displayed-to-user layout state before fitting. A failure in one diagram should not prevent slide navigation; report it and preserve readable source or a nonblocking fallback.

### 11.3 Independent proportional media fitting

The fitting algorithm is **browser-side, layout-based, best effort**:

1. Establish each slide's usable body content rectangle from computed section geometry, actual padding and reserved header/footer/pagination areas.
2. Lay out text/table/code content at theme-determined sizes without automatic shrinking; treat them as fixed consumers of space.
3. For each image/diagram, measure its intrinsic ratio (`naturalWidth`/`naturalHeight` or SVG `viewBox`/measurable bounds) and its preferred display size from CSS, preserving aspect ratio.
4. Constrain each media item to usable width. Allocate remaining height among media in proportion to their preferred heights; shrink independently as necessary, preserving each aspect ratio. **Never enlarge media merely to consume spare space**. Reevaluate if line wrapping changes due to media-width constraints.
5. If available height is zero/negative or no valid intrinsic bounds exist, avoid negative/NaN dimensions, keep an accessible fallback, and emit a warning.
6. After fitting, if any content extends beyond the defined body rectangle, emit `W_SLIDE_OVERFLOW` with slide index and measured excess dimensions. Do not shrink text, crop media to hide the error, or silently scroll.

For complex interleaved text/media, fitting need not solve a general constraint optimization problem; the required outcome is bounded, stable and deterministic for a given browser/viewport/font state, with an explicit warning when content cannot fit. Exact pixels may vary across browser engines even though the compiled HTML bytes are identical.

## 12. Static validation and diagnostics

**Fatal compile-time examples:** malformed/nonmapping/duplicate-key YAML, absent required frontmatter, invalid explicitly specified `layout`/`theme`, missing referenced CSS or missing bundled default CSS, unknown frontmatter key, forbidden local CSS `url`, CSS `@import`, missing/unsafe/unsupported image, unlabeled code fence, unsupported explicit Marp directive, raw HTML block/inline markup, empty slide, input decoding error, unsafe URL scheme, or unsupported explicitly detected Markdown construct.

**Nonfatal compile-time examples:** unknown labelled code-fence language (plain `<pre>`), relative Markdown hyperlink whose target is not guaranteed to remain portable, optional benign ignored HTML comments (if otherwise allowed by section 6).

**Browser-only examples:** Mermaid syntax/render exception, Prism/CDN load error, missing HTTPS font or CSS resource, unsupported browser API, slide overflow after rendering, SVG without measurable intrinsic geometry.

Diagnostics must have stable machine-readable codes and human-readable explanation. Compile errors are collected where safe; the compiler may stop parsing when subsequent detection is impossible. It must never output a nominal success when a known fatal violation occurred. On success, warnings are printed to stderr; optional short success message goes to stdout.

**Security stance:** local author input is treated as untrusted HTML/JS; escape all Markdown-derived text and attributes. Don't execute raw HTML or arbitrary YAML-injected JS. Sanitize/restrict CSS closing tags, Mermaid security options, and embedded SVG external resources. This is not a claim of a robust sandbox against malicious third-party CSS or browser dependencies; presentations should use trusted stylesheets.

## 13. Determinism and performance

- Identical Markdown/CSS/image bytes, pinned compiler+dependency version, and deterministic configuration produce byte-identical HTML across repeated builds. Runtime visual rendering is *not* promised pixel-identical across browsers.
- No network traffic in the compile step; local filesystem IO only.
- Avoid recompiling unchanged images multiple times within a single build (cache by resolved file path for the build lifetime). No persistent cache is required.
- The HTML contains no bundled copies of Prism/Mermaid; on a fresh browser without CDN access, highlighted source text remains readable and Mermaid may remain as source with a console error.
- No performance guarantee is specified in milliseconds; acceptance criterion is a quick local one-shot command for normal-size decks, without spawning browser or Node processes.

## 14. Acceptance test matrix (required before marking v1 complete)

### A. CLI, frontmatter and splitting

| ID | Test | Pass condition |
|---|---|---|
| A01 | Valid Markdown + two explicit CSS paths | One sibling `.html`, embedded styles in layout/theme order, exit 0. |
| A02 | Run from unrelated working directory | CSS/images resolve relative to Markdown, not CWD. |
| A03 | Rebuild same inputs twice | SHA-256 of emitted HTML identical. |
| A04 | Existing output and new fatal error | Existing output bytes preserved; exit 1. |
| A05 | Malformed YAML, duplicate key, or invalid/empty optional CSS path | Fatal diagnostic with useful location; no replacement output. |
| A06 | Frontmatter followed by two `---` slide boundaries | Exactly three sections with correct slide order. |
| A07 | `---` inside fenced code | Not treated as slide delimiter. |
| A08 | `***` or `___` in content | Render `<hr>`, not a new slide. |
| A09 | Leading/trailing/adjacent slide delimiters | Fatal empty-slide error. |
| A10 | Unexpected raw HTML and Marpit comment directive | Fatal; no script or injected markup appears in output. |

### B. Content and code fences

| ID | Test | Pass condition |
|---|---|---|
| B01 | GFM headings/lists/tables/task lists/quotes | Correct semantic structure; no unnecessary typographic wrappers. |
| B02 | `txt` fence containing `<a>&` | Escaped plain `<pre>`, no Prism language class. |
| B03 | `cs`, `cpp`, `java` fences | Canonical Prism markup and correctly ordered pinned dependencies. |
| B04 | Duplicate aliases (`cs`/`csharp`) | Grammar included once. |
| B05 | Unknown labelled fence | Warning and escaped plain `<pre>`; build succeeds. |
| B06 | Unlabelled fence | Fatal `E_MISSING_CODE_LANGUAGE`. |
| B07 | Mermaid fence including `---` | One Mermaid `<pre>`, no Prism class; delimiter preserved as diagram text. |
| B08 | No code fences | No Prism runtime emitted. |
| B09 | No Mermaid fences | No Mermaid ESM import emitted. |
| B10 | Source code containing HTML/script strings | Rendered visibly as text, not executed. |

### C. Image and CSS assets

| ID | Test | Pass condition |
|---|---|---|
| C01 | Local JPEG/PNG/SVG/WebP/GIF | Correct MIME Data URL, base64 decodes byte-for-byte to input. |
| C02 | Missing image | Fatal and no output overwrite. |
| C03 | Markdown image from nested source directory | Paths resolve correctly relative to Markdown file. |
| C04 | SVG containing script or external references | Rejected or sanitized according to documented safety policy; no active content. |
| C05 | CSS `url(./font.woff2)` | Fatal local CSS asset violation. |
| C06 | CSS `url(https://...)` | Preserved URL; no compilation-time HTTP request. |
| C07 | CSS `@import` | Fatal. |
| C08 | Explicitly referenced or bundled default CSS missing/unreadable | Fatal, with no silent fallback for an invalid explicit path. |
| C09 | Embedded CSS with `</style>` injection attempt | Rejected or safely encoded so no injected HTML/JS executes. |
| C10 | Neither `layout` nor `theme` in frontmatter | Both compiler-bundled defaults are embedded, layout before theme. |
| C11 | Only `layout` is present | Explicit Markdown-relative layout CSS + bundled default theme CSS. |
| C12 | Only `theme` is present | Bundled default layout CSS + explicit Markdown-relative theme CSS. |
| C13 | Both stylesheet keys omitted, invocation from another working directory | Defaults resolve from compiler directory; output still lands beside Markdown. |
| C14 | Explicit CSS path missing though default exists | Fatal; do not silently substitute bundled CSS. |
| C15 | Flat and nested input directories | Image and CSS paths resolve correctly; unused assets are not bundled. |

### D. Browser rendering, fitting and controls

| ID | Test | Pass condition |
|---|---|---|
| D01 | Wide and tall browser viewports | Entire 16:9 slide visible, centered, without page scrolling. |
| D02 | Typography on two viewport sizes | Responsive font sizing follows CSS theme, not JS text-shrinking. |
| D03 | Header/footer + pagination | Reserved areas do not overlap normal body content in conforming layout CSS. |
| D04 | `paginate: false` | No pagination number or pagination attributes. |
| D05 | Keyboard navigation | Right/Space/PageDown, Left/PageUp, Home/End work; limits clamp. |
| D06 | Two mixed images plus text | Images independently retain aspect ratios and fit available region when feasible. |
| D07 | Large Mermaid plus heading | Diagram becomes SVG, fit runs after render, aspect ratio retained. |
| D08 | Resize after Mermaid render | Layout and media recomputed without duplicate diagrams. |
| D09 | Intentionally overfull text/table/code slide | Console `W_SLIDE_OVERFLOW`; text unchanged; no slide scrolling. |
| D10 | Invalid Mermaid syntax | Console error with slide number; navigation continues; no compile-time claim of syntax validity. |
| D11 | Prism and Mermaid together | Highlighting applies to source code only; diagram is not highlighted. |
| D12 | CDN unavailable | Plain code/text slides remain navigable; runtime reports missing dependencies. |
| D13 | CSS with remote font load delay | Fitting reruns once fonts settle; no permanently stale dimensions. |

### E. Security, diagnostics and reproducibility

| ID | Test | Pass condition |
|---|---|---|
| E01 | Invalid image URI scheme | Fatal diagnostic; no executable URL in generated HTML. |
| E02 | Frontmatter HTML strings | Header/footer text is escaped. |
| E03 | Unknown `mermaid` configuration key | Fatal rather than silently interpreted. |
| E04 | Multiple independent source faults | Multiple diagnostics reported where parsing remains possible. |
| E05 | HTML output examined | No timestamps, random IDs, absolute machine paths, or compiler network calls. |
| E06 | CSS/theme semantic contract fixture | Known reference theme renders intended headings, lists, tables, code, media. |

**Manual golden fixtures:** at least three Markdown files and their reference HTML files: (1) GFM text/table deck; (2) Mermaid/code/images architecture deck; (3) minimalist theme deck. Snapshot comparisons should exclude volatile browser-rendered SVG markup, which is a runtime artifact rather than a compiler artifact.

## 15. Implementation gate and open assumptions

Do **not** generate implementation code until this specification is approved. The next step is reviewing the specification and resolving the remaining design-policy assumptions below, not adding features by implication:

1. The `layout` YAML key names the first CSS file and `theme` names the second. Both keys are optional under the newly approved default-styles amendment. The exact `layout` key name is a compiler-specific convention.
2. Empty slides are treated as errors, even though Markdown could technically describe them.
3. CSS `@import` is banned and CSS remote URLs are allowed; this makes the two explicit CSS inputs authoritative while still permitting CDN-hosted fonts.
4. Generic HTML comments are discarded; HTML-comment Marpit directives are rejected. The distinction should be covered by parser tests.
5. Mermaid's configuration surface is intentionally limited to `mermaid.theme` to avoid arbitrary dynamic configuration injection.
6. Automatic independent fitting is best effort, not a guarantee of printable/readable diagrams on text-dense slides.
7. Markdown local image paths are limited to the Markdown directory tree for portability and safety; this is stricter than “relative to Markdown” alone. If shared assets elsewhere are essential, this restriction should be revisited.
8. The actual Python GFM parser and Prism dependency-manifest snapshot must be selected and locked during implementation, with compatibility validated in tests.
9. Prism 1.29.0 and Mermaid 12.0.0 are **candidate exact pins** requiring verification on first release; no unpinned versions are acceptable in released output.
10. Two **resolved** CSS files are always required. The generator installation must ship usable `base.css` and `theme.css` defaults, but this specification phase still produces no implementation CSS files; tests must verify the bundled defaults and user-supplied overrides.

## 16. External normative references

- Marpit's semantic slide sections and pagination conventions: https://marpit.marp.app/theme-css
- Mermaid rendering API and explicit `mermaid.run()` lifecycle: https://mermaid.js.org/config/usage
- Mermaid setup and `<pre class="mermaid">`: https://mermaid.js.org/intro/getting-started
- PrismJS language grammars and aliases: https://prismjs.com/
- GFM specification: https://github.github.com/gfm/

Where this document contradicts Marpit, Mermaid examples or generic Markdown behavior, **this project's explicit contract takes precedence**, subject to using the third-party APIs as actually documented.
