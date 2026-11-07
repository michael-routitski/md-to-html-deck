"""Fenced code rendering and the pinned Prism component registry.

No code is executed by this module. Languages are deliberately allowlisted;
unknown *labelled* fences become escaped plain text with a warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re

PRISM_VERSION = "1.29.0"
MERMAID_VERSION = "12.0.0"
CDN = "https://cdn.jsdelivr.net/npm"

# Version-matched subset of Prism 1.29.0's components dependency graph.
# A stable, explicit registry also acts as the supported language contract.
GRAMMAR_DEPS = {
    "markup": (),
    "css": (),
    "clike": (),
    "javascript": ("clike",),
    "typescript": ("javascript",),
    "c": ("clike",),
    "cpp": ("c",),
    "csharp": ("clike",),
    "java": ("clike",),
    "python": (),
    "bash": (),
    "json": (),
    "yaml": (),
    "sql": (),
    "powershell": ("clike",),
}
ALIASES = {
    "html": "markup", "xml": "markup", "svg": "markup", "markup": "markup",
    "cs": "csharp", "c#": "csharp", "csharp": "csharp",
    "c++": "cpp", "cpp": "cpp", "cxx": "cpp",
    "c": "c", "js": "javascript", "javascript": "javascript",
    "ts": "typescript", "typescript": "typescript",
    "py": "python", "python": "python",
    "sh": "bash", "shell": "bash", "bash": "bash",
    "yml": "yaml", "yaml": "yaml", "ps1": "powershell",
    "pwsh": "powershell", "powershell": "powershell",
    **{key: key for key in GRAMMAR_DEPS},
}
PLAIN = {"txt", "text", "plaintext"}


@dataclass(frozen=True)
class FenceResult:
    html: str
    language: str | None = None
    mermaid: bool = False
    warning: str | None = None


class FenceError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def render_fence(source: str, info: str | None, *, fenced: bool = True) -> FenceResult:
    if not fenced:
        raise FenceError("E_MISSING_CODE_LANGUAGE", "Indented code blocks are not supported; use a labelled fenced block")
    if not info or not info.strip():
        raise FenceError("E_MISSING_CODE_LANGUAGE", "Every fenced code block must declare a language")
    label = info.strip().lower()
    if re.search(r"\s", label):
        raise FenceError("E_CODE_FENCE_INFO", "Code-fence info strings may contain only a language identifier")
    escaped = escape(source, quote=False)
    if label in PLAIN:
        return FenceResult(f"<pre>{escaped}</pre>\n")
    if label == "mermaid":
        if re.search(r"%%\s*\{\s*init\s*:", source, re.I) or re.search(r"^\s*---\s*\n\s*config\s*:", source):
            raise FenceError("E_MERMAID_DIRECTIVE", "Per-diagram Mermaid configuration directives are not supported")
        return FenceResult(f'<pre class="mermaid">{escaped}</pre>\n', mermaid=True)
    canonical = ALIASES.get(label)
    if canonical not in GRAMMAR_DEPS:
        return FenceResult(f"<pre>{escaped}</pre>\n", warning=f"W_UNKNOWN_CODE_LANGUAGE: '{label}' is not a supported Prism language; using plain text")
    return FenceResult(
        f'<pre class="language-{canonical}"><code class="language-{canonical}">{escaped}</code></pre>\n',
        language=canonical,
    )


def prism_components(languages: set[str]) -> list[str]:
    """Topologically order required grammar components; each appears once."""
    result: list[str] = []
    seen: set[str] = set()
    def add(name: str) -> None:
        if name in seen:
            return
        if name not in GRAMMAR_DEPS:
            raise ValueError(f"Unsupported Prism component {name}")
        for dependency in GRAMMAR_DEPS[name]:
            add(dependency)
        seen.add(name)
        result.append(name)
    for lang in sorted(languages):
        add(lang)
    return result
