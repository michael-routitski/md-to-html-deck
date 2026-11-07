#!/usr/bin/env python3
"""Compile one Markdown presentation to an atomically replaced sibling HTML file.

Usage: python compile.py /path/to/presentation.md
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

import tinycss2

from html_runtime import assemble
from markdown_engine import Issue, parse_deck


def check_css(text: str, name: str) -> list[Issue]:
    issues = []
    if "</style" in text.lower() or "<script" in text.lower():
        issues.append(Issue("ERROR", "E_CSS_ESCAPE", f"{name}: HTML/script escape sequences cannot occur in CSS"))
    rules = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True)

    def check_nodes(nodes):
        for t in nodes:
            if t.type == "error":
                issues.append(Issue("ERROR", "E_CSS_SYNTAX", f"{name}: {t.message}"))
            if t.type == "at-rule" and t.lower_at_keyword == "import":
                issues.append(Issue("ERROR", "E_CSS_IMPORT", f"{name}: @import is forbidden; use an HTTPS url(...) in a rule"))
            if t.type == "url":
                check_url(t.value)
            if t.type == "function":
                if t.lower_name == "url":
                    raw = tinycss2.serialize(t.arguments).strip()
                    if len(raw) > 1 and raw[0] in "\"'" and raw[-1] == raw[0]:
                        raw = raw[1:-1]
                    check_url(raw)
                else:
                    check_nodes(t.arguments)
            for attr in ("content", "prelude"):
                children = getattr(t, attr, None)
                if isinstance(children, list):
                    check_nodes(children)

    def check_url(value: str):
        lower = value.strip().lower()
        if not lower.startswith(("https://", "data:", "#")):
            issues.append(Issue("ERROR", "E_CSS_ASSET", f"{name}: local/insecure CSS URL is forbidden: {value}"))

    check_nodes(rules)
    return issues


def resolve_css(deck_dir: Path, compiler_dir: Path, meta: dict) -> tuple[list[str], list[Issue]]:
    styles = []
    issues = []
    for key, filename in (("layout", "base.css"), ("theme", "theme.css")):
        explicit = key in meta
        path = (deck_dir / meta[key]) if explicit else (compiler_dir / filename)
        if explicit and (Path(meta[key]).is_absolute() or Path(meta[key]).suffix.lower() != ".css"):
            issues.append(Issue("ERROR", "E_CSS_PATH", f"'{key}' must name a relative .css file"))
            styles.append("")
            continue
        try:
            css = path.resolve().read_text(encoding="utf-8")
        except (OSError, UnicodeError) as e:
            issues.append(Issue("ERROR", "E_CSS_READ", f"Cannot read {key} CSS at {path}: {e}"))
            css = ""
        if css:
            issues.extend(check_css(css, f"{key} ({path.name})"))
        styles.append(css)
    return styles, issues


def compile_presentation(input_path: Path, compiler_dir: Path) -> int:
    try:
        source = input_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as e:
        print(f"{input_path}: ERROR [E_INPUT_READ] {e}", file=sys.stderr)
        return 2

    deck = parse_deck(source, input_path.resolve().parent)
    styles = ["", ""]
    css_issues = []
    if deck.meta:
        styles, css_issues = resolve_css(input_path.resolve().parent, compiler_dir, deck.meta)
    # Empty YAML mapping is a valid (defaults-only) frontmatter.
    elif not deck.errors:
        styles, css_issues = resolve_css(input_path.resolve().parent, compiler_dir, deck.meta)

    problems = deck.issues + css_issues
    for p in problems:
        loc = f"{input_path}:{p.line}" if p.line is not None else str(input_path)
        print(f"{loc}: {p.severity} [{p.code}] {p.message}", file=sys.stderr)
    if any(p.severity == "ERROR" for p in problems):
        return 1

    try:
        html = assemble(deck.slides, deck.meta, styles[0], styles[1], deck.languages, deck.has_mermaid)
        output = input_path.with_suffix(".html")
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=output.parent, prefix=f".{output.stem}.",
                                             suffix=".tmp", delete=False) as temp:
                tmp_path = Path(temp.name)
                temp.write(html)
            os.replace(tmp_path, output)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()
        print(f"Compiled {len(deck.slides)} slide(s): {output}")
        return 0
    except (OSError, UnicodeError, ValueError) as e:
        print(f"{input_path}: ERROR [E_OUTPUT] {e}", file=sys.stderr)
        return 2


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].lower().endswith(".md"):
        print("Usage: python compile.py <presentation.md>", file=sys.stderr)
        return 2
    source = Path(argv[1])
    if not source.is_file():
        print(f"{source}: ERROR [E_INPUT_READ] Markdown file not found", file=sys.stderr)
        return 2
    return compile_presentation(source, Path(__file__).resolve().parent)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
