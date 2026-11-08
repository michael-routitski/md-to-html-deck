"""Deterministic standalone-HTML assembly and minimal presentation runtime."""

from __future__ import annotations

from html import escape
import json

from code_fences import CDN, MERMAID_VERSION, PRISM_VERSION, prism_components

RUNTIME_JS = r"""
(() => {
  'use strict';
  const slides = [...document.querySelectorAll('.deck > section.slide')];
  let current = 0;
  let scheduled = false;
  const diagnostic = (level, code, slide, message) => {
    console[level](`[${code}] slide ${slide}: ${message}`);
  };

  function activate(n) {
    current = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((slide, i) => {
      const active = i === current;
      slide.dataset.active = String(active);
      slide.setAttribute('aria-hidden', String(!active));
      slide.inert = !active;
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.target && (e.target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName))) return;
    const action = {
      ArrowRight: current + 1, PageDown: current + 1, ' ': current + 1,
      ArrowLeft: current - 1, PageUp: current - 1, Home: 0, End: slides.length - 1,
    };
    if (!(e.key in action)) return;
    e.preventDefault();
    activate(action[e.key]);
  });
  activate(0);

  function dimensions(el, usableWidth) {
    if (el.matches('img')) {
      const w = el.naturalWidth || el.getBoundingClientRect().width;
      const h = el.naturalHeight || el.getBoundingClientRect().height;
      if (!(w > 0 && h > 0)) return null;
      const pref = Math.min(w, usableWidth);
      return { w: pref, h: pref * h / w, ratio: w / h };
    }
    const svg = el.querySelector('svg');
    if (!svg) return null;
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const rect = svg.getBoundingClientRect();
    const w = vb && vb.width > 0 ? vb.width : rect.width;
    const h = vb && vb.height > 0 ? vb.height : rect.height;
    if (!(w > 0 && h > 0)) return null;
    const pref = Math.min(w, usableWidth);
    return { w: pref, h: pref * h / w, ratio: w / h };
  }

  function fit(slide, slideIndex) {
    const style = getComputedStyle(slide);
    const paddingTop = parseFloat(style.paddingTop) || 0;
    const paddingBottom = parseFloat(style.paddingBottom) || 0;
    const paddingLeft = parseFloat(style.paddingLeft) || 0;
    const paddingRight = parseFloat(style.paddingRight) || 0;
    const usableHeight = Math.max(0, slide.clientHeight - paddingTop - paddingBottom);
    const usableWidth = Math.max(0, slide.clientWidth - paddingLeft - paddingRight);
    const media = [...slide.querySelectorAll('img, pre.mermaid')];

    // Reset prior fit sizes before re-measuring on resize or font changes.
    media.forEach(el => {
      el.style.removeProperty('width');
      el.style.removeProperty('height');
      el.style.removeProperty('max-height');
    });
    const items = media.map(el => ({ el, dims: dimensions(el, usableWidth) }));
    for (const item of items) {
      if (!item.dims) {
        if (!item.el.matches('pre.mermaid') || item.el.querySelector('svg')) {
          diagnostic('warn', 'W_MEDIA_GEOMETRY', slideIndex, 'Media has no measurable dimensions');
        }
        continue;
      }
      item.el.style.width = `${item.dims.w}px`;
      item.el.style.height = `${item.dims.h}px`;
    }

    // Measure normal-flow content, including mixed text and media.
    const content = [...slide.children].filter(x => !x.matches('header, footer'));
    if (content.length && items.length) {
      const top = Math.min(...content.map(x => x.getBoundingClientRect().top));
      const bottom = Math.max(...content.map(x => x.getBoundingClientRect().bottom));
      const used = Math.max(0, bottom - top);
      const prefTotal = items.reduce((sum, x) => sum + (x.dims ? x.dims.h : 0), 0);
      const nonMedia = Math.max(0, used - prefTotal);
      const allocated = Math.max(0, usableHeight - nonMedia);
      const factor = prefTotal > 0 ? Math.min(1, allocated / prefTotal) : 1;
      for (const item of items) {
        if (!item.dims) continue;
        const h = Math.max(0, item.dims.h * factor);
        const w = Math.max(0, h * item.dims.ratio);
        item.el.style.width = `${w}px`;
        item.el.style.height = `${h}px`;
      }
    }

    const sRect = slide.getBoundingClientRect();
    const limits = {
      left: sRect.left + paddingLeft, right: sRect.right - paddingRight,
      top: sRect.top + paddingTop, bottom: sRect.bottom - paddingBottom,
    };
    let extraX = 0, extraY = 0;
    for (const item of slide.querySelectorAll('h1,h2,h3,h4,h5,h6,p,ul,ol,blockquote,table,pre,hr,img')) {
      const r = item.getBoundingClientRect();
      if (!r.width && !r.height) continue;
      extraX = Math.max(extraX, limits.left - r.left, r.right - limits.right, item.scrollWidth - item.clientWidth);
      extraY = Math.max(extraY, limits.top - r.top, r.bottom - limits.bottom, item.scrollHeight - item.clientHeight);
    }
    if (extraX > 8 || extraY > 8) {
      diagnostic('warn', 'W_SLIDE_OVERFLOW', slideIndex,
        `content exceeds body region by ${Math.ceil(extraX)}px horizontally, ${Math.ceil(extraY)}px vertically`);
    }
  }

  function recompute() {
    for (let i = 0; i < slides.length; ++i) fit(slides[i], i + 1);
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      recompute();
    });
  }
  window.addEventListener('resize', schedule, { passive: true });
  const ready = (async () => {
    // The runtime script appears before deferred CDN scripts execute. Wait for
    // DOMContentLoaded so Prism core and grammars are ready before highlighting.
    if (document.readyState === 'loading') {
      await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve, { once: true }));
    }
    if (document.fonts && document.fonts.ready) {
      try { await document.fonts.ready; }
      catch (err) { console.warn('[W_FONT_READY]', err); }
    }
    await Promise.all([...document.images].map(img => {
      if (img.complete) return Promise.resolve();
      return img.decode ? img.decode().catch(() => {}) : new Promise(resolve => {
        img.addEventListener('load', resolve, { once: true });
        img.addEventListener('error', resolve, { once: true });
      });
    }));
    if (document.querySelector('pre[class*="language-"]')) {
      if (window.Prism && typeof window.Prism.highlightAll === 'function') {
        window.Prism.highlightAll();
      } else {
        console.error('[E_PRISM_CDN] Prism scripts unavailable. Source code remains readable.');
      }
    }
    schedule();
  })();
  if (document.fonts && document.fonts.addEventListener) {
    document.fonts.addEventListener('loadingdone', schedule);
  }
  window.__slideRuntime = { ready, schedule, diagnostic };
})();
"""


def assemble(slides: list[str], meta: dict, layout_css: str, theme_css: str,
             languages: set[str], has_mermaid: bool) -> str:
    parts = [
        "<!doctype html>\n<html lang=\"en\">\n<head>\n",
        '  <meta charset="utf-8">\n',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n',
        "  <title>Presentation</title>\n",
        f'  <style id="slide-layout">\n{layout_css}\n  </style>\n',
        f'  <style id="slide-theme">\n{theme_css}\n  </style>\n',
    ]
    if languages:
        prefix = f"{CDN}/prismjs@{PRISM_VERSION}/components/"
        parts += [
            "  <script>window.Prism = window.Prism || {}; window.Prism.manual = true;</script>\n",
            f'  <script defer src="{prefix}prism-core.min.js"></script>\n',
        ]
        for lang in prism_components(languages):
            parts.append(f'  <script defer src="{prefix}prism-{lang}.min.js"></script>\n')
    parts.extend(["</head>\n<body>\n", '  <div class="deck">\n'])
    total = len(slides)
    for i, body in enumerate(slides, 1):
        attr = f' data-page="{i}" data-total-pages="{total}"' if meta.get("paginate", False) else ""
        active = ' data-active="true"' if i == 1 else ""
        parts.append(f'    <section class="slide"{attr}{active}>\n')
        if meta.get("header"):
            parts.append(f'      <header>{escape(meta["header"])}</header>\n')
        parts.append(body)
        if meta.get("footer"):
            parts.append(f'      <footer>{escape(meta["footer"])}</footer>\n')
        parts.append("    </section>\n")
    parts.extend(['  </div>\n', f'  <script>\n{RUNTIME_JS}\n  </script>\n'])
    if has_mermaid:
        version = f"{CDN}/mermaid@{MERMAID_VERSION}/dist/mermaid.esm.min.mjs"
        mermaid_theme = json.dumps(meta.get("mermaid", {}).get("theme", "default"))
        # Dynamic module import permits a controlled network error path.
        parts.append('  <script type="module">\n')
        parts.append(f"    const url = {json.dumps(version)};\n")
        parts.append('    const runtime = window.__slideRuntime;\n')
        parts.append('    try {\n')
        parts.append('      await runtime.ready;\n')
        parts.append('      const { default: mermaid } = await import(url);\n')
        parts.append(f"      mermaid.initialize({{ startOnLoad: false, securityLevel: 'strict', theme: {mermaid_theme} }});\n")
        parts.append("      const nodes = [...document.querySelectorAll('pre.mermaid')];\n")
        parts.append('      for (const node of nodes) {\n')
        parts.append('        const original = node.textContent;\n')
        parts.append('        try { await mermaid.run({ nodes: [node] }); }\n')
        parts.append('        catch (err) {\n')
        parts.append('          node.textContent = original;\n')
        parts.append("          const slide = [...document.querySelectorAll('.deck > section.slide')].indexOf(node.closest('section')) + 1;\n")
        parts.append("          runtime.diagnostic('error', 'E_MERMAID_RENDER', slide, String(err));\n")
        parts.append('        }\n')
        parts.append('      }\n')
        parts.append('      runtime.schedule();\n')
        parts.append('    } catch (err) { console.error(`[E_MERMAID_CDN] Could not import ${url}`, err); }\n')
        parts.append('  </script>\n')
    parts.extend(["</body>\n</html>\n"])
    return "".join(parts)
