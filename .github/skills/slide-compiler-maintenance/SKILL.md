---
name: slide-compiler-maintenance
description: Diagnose, debug, test and safely modify this project's deterministic Python Markdown-to-HTML slide compiler. Use for build failures, incorrect Markdown parsing, CSS resolution, image embedding, Prism language loading, Mermaid rendering, browser slide navigation, overflow and compiler architecture changes.
---

# Slide compiler maintenance

## Mission and source of truth

Maintain the **small, deterministic Markdown-to-static-HTML presentation compiler**. Prefer a small, reproducible fix over architectural expansion. The system is deliberately not Marpit, a general-purpose presentation framework, an AI-backed generator, a Node build pipeline or a web server.

At session start:

1. Locate the repository root and read `SPEC.md` (or find the project's specification if located elsewhere). Treat it as the intended contract; if it conflicts with code, identify the mismatch rather than silently inventing behaviour.
2. Inspect the actual `compile.py`, `markdown_engine.py`, `code_fences.py`, `html_runtime.py`, `base.css`, `theme.css`, and `requirements.txt` before claiming how anything works. The names below describe the original design, not a guarantee that code has not changed.
3. Locate a representative deck (`presentation.md`, preferably the sample). Check whether the deck supplies explicit `layout` and `theme` paths or uses compiler defaults.
4. State the symptom, an evidence-backed suspected layer, a minimal reproduction, and the success criterion before editing.

## Architecture map

| File | Responsibility | Typical defects |
| --- | --- | --- |
| `compile.py` | CLI, CSS validation/resolution, diagnostics, atomic output replacement | Incorrect paths, CSS validation, overwrite or failure semantics |
| `markdown_engine.py` | Safe YAML, GFM parsing, slide splitting, semantic HTML, local image validation/embedding | Fence separators, frontmatter, links/images, malformed HTML |
| `code_fences.py` | Fenced-block classification, escaping, Prism aliases/dependency ordering, Mermaid source markup | Wrong language aliases, unlabelled fences, broken grammar loading |
| `html_runtime.py` | Single-file HTML assembly, pinned CDN references, client-side navigation, Mermaid/Prism initialization, media fitting and overflow diagnostics | Browser errors, hidden-slide sizing, async initialization, layout timing |
| `base.css` | Responsive 16:9 geometry, single visible slide, reserved header/footer area, media containment | Overflow, centering, scaling, hidden-slide mechanics |
| `theme.css` | Semantic typography, colour, spacing, code/table/diagram appearance | Theme-specific visual regressions |

**Data flow:** Markdown + optional deck CSS + local images → parse and validate → semantic `<section>` slides → inline layout/theme CSS + base64 images → pinned Prism/Mermaid CDN references (only when needed) + small browser runtime → `presentation.html` adjacent to the Markdown.

## Invariants: do not break

- CLI: `python compile.py /path/to/presentation.md`; output is sibling `presentation.html`. No extra mandatory arguments. The current implementation uses `mistune`, `PyYAML`, and `tinycss2`; install pinned dependencies from `requirements.txt`.
- Input has YAML frontmatter. `layout` and `theme` are **optional independent overrides**. If omitted, resolve `base.css` or `theme.css` from the compiler installation directory. If explicitly supplied, resolve each relative to the Markdown file; an invalid or missing explicit CSS file is fatal, never silently defaulted.
- Only standalone `---` outside frontmatter and fenced code separates slides. Markdown is GFM-oriented. Do not treat Mermaid diagram syntax as Markdown slide delimiters.
- No raw HTML in Markdown. No per-slide styling directives or arbitrary Marpit compatibility. Fenced blocks **must have a language**. `txt`/`text`/`plaintext` → escaped `<pre>`; known source language → Prism `<pre><code class="language-...">`; `mermaid` → escaped `<pre class="mermaid">` (no Prism); unknown *labelled* language → warning and escaped plain text.
- Preserve semantic `.marpit > section` structure, optional header/footer and Marpit-style pagination attributes. CSS controls browser-responsive 16:9 geometry; do not replace this with an undocumented fixed canvas.
- Embed local Markdown JPEG, PNG, SVG, WebP, and GIF images as data URLs. Paths are Markdown-relative; enforce path restrictions and safe SVG handling. CSS may use HTTPS or data URLs but not local `url(...)` or `@import`.
- Stylesheets are embedded **layout first, theme second**. Do not add structural wrapper elements around slide typography unless a contract change is explicitly approved.
- Browser runtime shows one slide at a time: Right/PageDown/Space next; Left/PageUp previous; Home/End boundaries. No visible navigation controls. Text is **not** automatically shrunk; images and Mermaid diagrams may be proportionally fit. Runtime diagnostics belong in the browser console.
- Prism and Mermaid are pinned in `code_fences.py`. Compiler must not fetch the network. Browser may require CDN connectivity; single-file is **not fully offline**. Mermaid rendering errors are normally browser-time, not compile-time.
- Do not write/replace HTML on a fatal compile error. On success, replace output atomically. Identical inputs and versions should yield byte-identical HTML; no timestamps/random IDs or network effects.

## Troubleshooting workflow

1. **Reproduce** the exact invocation, working directory, source Markdown, CSS and assets; capture exit code and stderr. Do not edit the original deck as a first debugging step.
2. **Classify** the failure: CLI/input → YAML/slides → fences/GFM → media/CSS → HTML assembly → CDN/Prism/Mermaid → navigation/measurement/theme. Inspect the smallest responsible file first.
3. **Reduce** to a tiny fixture in a temporary directory. Include only relevant Markdown/frontmatter and, if needed, a minimal CSS file or asset.
4. **Distinguish** compilation success from browser rendering success. Inspect emitted HTML and console/network errors. For Mermaid, check CDN import, parse/render failure, SVG replacement and subsequent resizing separately. For Prism, check script defer/order, grammar prerequisites, language class names and highlighting initialization. Hidden-slide SVG dimensions can be zero if measured while non-measurable.
5. **Patch narrowly**. Preserve public contracts and unchanged file responsibilities. If a change alters the agreed Markdown, YAML, HTML or CSS semantics, identify the compatibility impact and update `SPEC.md` only with user approval or a clearly requested contract change.
6. **Regression-test** the bug plus neighbouring edge cases. Keep deterministic tests free of external network. Browser verification may require a local test runner/browser; do not claim live Mermaid/Prism CDN validation unless it was actually run.
7. **Report** root cause, files changed, commands/tests run and observed results; explicitly describe untested browser/network behaviour.

## Baseline smoke checks

From a project checkout with dependencies installed (adapt paths to the real repository):

```bash
python -m pip install -r md-slide-compiler/requirements.txt
python md-slide-compiler/compile.py my-presentation/presentation.md
```

If the compiler directory itself is the repository root, use `python -m pip install -r requirements.txt` and `python compile.py ../my-presentation/presentation.md` instead. Check that the output is a single HTML file, containing `<div class="marpit">`, one `<section>` per slide, two embedded `<style>` blocks, expected Prism language classes, and raw escaped Mermaid definitions inside `<pre class="mermaid">` before client rendering. Re-run compilation and compare SHA-256 hashes of the HTML to detect nondeterminism. Verify that an intentionally missing CSS/image or an unlabelled code fence fails without clobbering the last good output.

For visual bugs, open the generated HTML in a current browser and test at 16:9 and non-16:9 viewport sizes. Test first/last slide navigation, font readiness, Mermaid diagrams on initially hidden slides, proportional media fitting, and console overflow warnings. When browser/CDN access is unavailable, report this as a limitation rather than asserting a visual pass.

## Change discipline

- Keep code readable and modules narrowly scoped; no framework introduction without demonstrated need.
- Add regression fixtures/tests when feasible, including expected compiler diagnostics and output semantics. Do not unnecessarily snapshot huge base64 payloads.
- Treat decks and their YAML/CSS/Mermaid as untrusted inputs: escape content and attributes; never execute their code or permit unsafe URL schemes to solve a formatting issue.
- Preserve default CSS fallback, clear errors, and CLI compatibility when reorganizing modules.
- If the request is actually to **author a presentation or theme**, use the `slide-deck-authoring` skill instead (or in addition, if a confirmed compiler bug needs fixing).
