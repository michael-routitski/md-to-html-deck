"""Source validation, GFM-to-semantic-HTML conversion and local asset embedding."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

import mistune
import yaml

from code_fences import FenceError, render_fence


class SourceError(ValueError):
    def __init__(self, code: str, message: str, line: int | None = None):
        super().__init__(message)
        self.code, self.line = code, line


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    line: int | None = None


@dataclass
class Deck:
    slides: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    languages: set[str] = field(default_factory=set)
    has_mermaid: bool = False
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> bool:
        return any(x.severity == "ERROR" for x in self.issues)

    def error(self, code: str, message: str, line: int | None = None) -> None:
        self.issues.append(Issue("ERROR", code, message, line))

    def warn(self, code: str, message: str, line: int | None = None) -> None:
        self.issues.append(Issue("WARNING", code, message, line))


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise SourceError("E_YAML_KEY", "Frontmatter keys must be strings", key_node.start_mark.line + 1)
        if key in result:
            raise SourceError("E_YAML_DUPLICATE", f"Duplicate YAML key: {key}", key_node.start_mark.line + 1)
        result[key] = loader.construct_object(value_node)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def frontmatter(source: str) -> tuple[dict, str, int]:
    source = source.lstrip("\ufeff")
    lines = source.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SourceError("E_FRONTMATTER", "YAML frontmatter must begin at the first line", 1)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            yaml_part = "".join(lines[1:i])
            try:
                config = yaml.load(yaml_part, Loader=UniqueKeyLoader)
            except yaml.YAMLError as e:
                line = getattr(getattr(e, "problem_mark", None), "line", None)
                raise SourceError("E_YAML", f"Invalid YAML frontmatter: {e}", (line + 2) if line is not None else None) from e
            if not isinstance(config, dict):
                raise SourceError("E_YAML_MAPPING", "Frontmatter must be a YAML mapping", 1)
            _validate_config(config)
            return config, "".join(lines[i + 1:]), i + 2
    raise SourceError("E_FRONTMATTER", "YAML frontmatter has no closing --- delimiter", 1)


def _validate_config(meta: dict) -> None:
    allowed = {"layout", "theme", "header", "footer", "paginate", "mermaid"}
    for key, value in meta.items():
        if key not in allowed:
            raise SourceError("E_YAML_UNKNOWN", f"Unsupported frontmatter key: {key}")
        if key in {"layout", "theme"}:
            if not isinstance(value, str) or not value.strip():
                raise SourceError("E_CSS_PATH", f"'{key}' must be a nonempty local CSS path")
        if key in {"header", "footer"} and not isinstance(value, str):
            raise SourceError("E_YAML_TYPE", f"'{key}' must be text")
    if "paginate" in meta and type(meta["paginate"]) is not bool:
        raise SourceError("E_YAML_TYPE", "'paginate' must be a YAML boolean")
    mermaid = meta.get("mermaid", {})
    if not isinstance(mermaid, dict) or any(k != "theme" for k in mermaid):
        raise SourceError("E_MERMAID_CONFIG", "'mermaid' accepts only a mapping containing 'theme'")
    if mermaid.get("theme", "default") not in {"default", "dark", "forest", "neutral", "base"}:
        raise SourceError("E_MERMAID_CONFIG", "Unsupported Mermaid theme")


# Fence-aware boundary scanner. Separators inside fenced code or block quotes
# are not interpreted as slides. Markdown parsing of each segment follows.
_OPEN_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def split_slides(body: str, first_line: int) -> list[tuple[str, int]]:
    slides = []
    current: list[str] = []
    line_start = first_line
    fence_char, fence_count = None, 0
    for n, line in enumerate(body.splitlines(keepends=True), first_line):
        stripped = line.rstrip("\r\n")
        marker = _OPEN_FENCE.match(stripped)
        if fence_char:
            if re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_count) + r",}[ \t]*", stripped):
                fence_char, fence_count = None, 0
            current.append(line)
            continue
        if marker:
            opener, rest = marker.groups()
            # Opening backtick fences cannot contain backticks in info string.
            if opener[0] != "`" or "`" not in rest:
                fence_char, fence_count = opener[0], len(opener)
            current.append(line)
            continue
        if stripped.strip() == "---" and not stripped.startswith("\t") and len(stripped) - len(stripped.lstrip(" ")) <= 3:
            if not "".join(current).strip():
                raise SourceError("E_EMPTY_SLIDE", "Leading or adjacent slide separator creates an empty slide", n)
            slides.append(("".join(current), line_start))
            current = []
            line_start = n + 1
        else:
            current.append(line)
    if not "".join(current).strip():
        raise SourceError("E_EMPTY_SLIDE", "Presentation is empty or ends with a slide separator", line_start)
    slides.append(("".join(current), line_start))
    return slides


def _clean_url(url: str, is_image: bool = False) -> str:
    url = url.strip()
    scheme = urlsplit(url).scheme.lower()
    if is_image:
        if not url or scheme or url.startswith(("/", "\\", "//")):
            raise SourceError("E_IMAGE_URL", f"Only local relative image paths are allowed: {url!r}")
        if "?" in url or "#" in url or "\\" in url:
            raise SourceError("E_IMAGE_URL", "Image paths must not contain query strings, fragments or backslashes")
    elif scheme not in {"", "https", "http", "mailto"} or url.startswith("//"):
        raise SourceError("E_LINK_URL", f"Unsafe hyperlink URL: {url!r}")
    return url


def _check_svg(data: bytes) -> None:
    upper = data.upper()
    if any(token in upper for token in (b"<!DOCTYPE", b"<!ENTITY", b"<?XML-STYLESHEET")):
        raise SourceError("E_UNSAFE_SVG", "SVG DTD/entities and stylesheet declarations are not permitted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise SourceError("E_IMAGE_FORMAT", f"Malformed SVG image: {e}") from e
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise SourceError("E_IMAGE_FORMAT", "SVG asset has no <svg> root")
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1].lower()
        if tag in {"script", "foreignobject", "iframe", "object", "embed", "image", "use"}:
            # Disallow indirection and executable elements, even via fragments.
            raise SourceError("E_UNSAFE_SVG", f"SVG contains unsupported element <{tag}>")
        for key, value in node.attrib.items():
            name = key.rsplit("}", 1)[-1].lower()
            if name.startswith("on") or name in {"href", "src"} and not value.startswith("#"):
                raise SourceError("E_UNSAFE_SVG", "SVG contains event handlers or external resources")
            if re.search(r"url\s*\(\s*['\"]?\s*(?!#)", value, re.I):
                raise SourceError("E_UNSAFE_SVG", "SVG contains external URL references")
        if tag == "style" and node.text and ("@import" in node.text.lower() or "url(" in node.text.lower()):
            raise SourceError("E_UNSAFE_SVG", "SVG stylesheet contains imports or external references")


def _mime_for(data: bytes, suffix: str) -> str:
    kinds = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".svg": "image/svg+xml",
        ".webp": "image/webp", ".gif": "image/gif",
    }
    mime = kinds.get(suffix.lower())
    if not mime:
        raise SourceError("E_IMAGE_FORMAT", f"Unsupported image extension: {suffix}")
    valid = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": data.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        "image/svg+xml": True,
    }
    if not valid[mime]:
        raise SourceError("E_IMAGE_FORMAT", f"Image content does not match {suffix} extension")
    if mime == "image/svg+xml":
        _check_svg(data)
    return mime


class HtmlTokens:
    def __init__(self, deck: Deck, root: Path, slide_number: int, line: int, image_cache: dict):
        self.deck, self.root, self.slide_number, self.line = deck, root, slide_number, line
        self.image_cache = image_cache
        self.container_stack: list[str] = []

    def _text(self, tokens) -> str:
        return "".join(t.get("raw", "") if t["type"] in {"text", "codespan"} else self._text(t.get("children", [])) for t in tokens)

    def _image(self, token) -> str:
        uri = _clean_url(token.get("attrs", {}).get("url", ""), is_image=True)
        alt = self._text(token.get("children", []))
        local = unquote(uri)
        file = (self.root / local).resolve()
        if not file.is_relative_to(self.root.resolve()):
            raise SourceError("E_IMAGE_PATH", f"Image escapes the Markdown directory: {uri}")
        if not file.is_file():
            raise SourceError("E_IMAGE_MISSING", f"Image file not found: {uri}")
        if file not in self.image_cache:
            try:
                raw = file.read_bytes()
            except OSError as e:
                raise SourceError("E_IMAGE_READ", f"Cannot read image {uri}: {e}") from e
            mime = _mime_for(raw, file.suffix)
            self.image_cache[file] = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
        title = token.get("attrs", {}).get("title")
        extra = f' title="{escape(title, quote=True)}"' if title else ""
        return f'<img src="{self.image_cache[file]}" alt="{escape(alt, quote=True)}"{extra}>'

    def _render_comment_or_container(self, raw: str) -> str:
        match = re.fullmatch(r"\s*<!--\s*(/?\w+)\s*-->\s*", raw)
        if match:
            tag = match.group(1).lower()
            if tag == "cards":
                self.container_stack.append("cards")
                return '<div class="cards">\n'
            elif tag == "/cards":
                if not self.container_stack or self.container_stack[-1] != "cards":
                    raise SourceError("E_UNCLOSED_CONTAINER", f"Slide {self.slide_number}: mismatched or unexpected '<!-- /cards -->' tag")
                self.container_stack.pop()
                return "</div>\n"
            elif tag == "card":
                self.container_stack.append("card")
                return '<div class="card">\n'
            elif tag == "/card":
                if not self.container_stack or self.container_stack[-1] != "card":
                    raise SourceError("E_UNCLOSED_CONTAINER", f"Slide {self.slide_number}: mismatched or unexpected '<!-- /card -->' tag")
                self.container_stack.pop()
                return "</div>\n"
        if re.fullmatch(r"\s*<!--(?:.|\n)*?-->\s*", raw):
            return ""
        raise SourceError("E_RAW_HTML", f"Slide {self.slide_number}: raw HTML is not supported")

    def render_many(self, tokens) -> str:
        out = "".join(self.render(token) for token in tokens)
        return out

    def finish(self) -> None:
        if self.container_stack:
            unclosed = self.container_stack[-1]
            raise SourceError("E_UNCLOSED_CONTAINER", f"Slide {self.slide_number}: unclosed container '<!-- {unclosed} -->'")

    def render(self, t: dict) -> str:
        typ = t["type"]
        attrs = t.get("attrs", {})
        child = lambda: self.render_many(t.get("children", []))
        if typ in {"blank_line"}: return ""
        if typ == "text": return escape(t.get("raw", ""), quote=False)
        if typ == "paragraph": return f"<p>{child()}</p>\n"
        if typ == "block_text": return child()
        if typ == "heading":
            level = attrs.get("level", 1)
            return f"<h{level}>{child()}</h{level}>\n"
        if typ in {"strong", "emphasis", "strikethrough"}:
            tag = {"strong": "strong", "emphasis": "em", "strikethrough": "del"}[typ]
            return f"<{tag}>{child()}</{tag}>"
        if typ == "codespan": return f"<code>{escape(t.get('raw', ''), quote=False)}</code>"
        if typ == "linebreak": return "<br>"
        if typ == "softbreak": return "\n"
        if typ == "thematic_break": return "<hr>\n"
        if typ == "link":
            url = _clean_url(attrs.get("url", ""))
            if not urlsplit(url).scheme and not url.startswith("#"):
                self.deck.warn("W_RELATIVE_LINK", f"Slide {self.slide_number}: relative link may not work when HTML is moved: {url}", self.line)
            title = attrs.get("title")
            extra = f' title="{escape(title, quote=True)}"' if title else ""
            return f'<a href="{escape(url, quote=True)}"{extra}>{child()}</a>'
        if typ == "image": return self._image(t)
        if typ == "block_quote": return f"<blockquote>\n{child()}</blockquote>\n"
        if typ == "list":
            ordered = attrs.get("ordered", False)
            tag = "ol" if ordered else "ul"
            start = attrs.get("start", 1)
            extra = f' start="{int(start)}"' if ordered and start != 1 else ""
            return f"<{tag}{extra}>\n{child()}</{tag}>\n"
        if typ in {"list_item", "task_list_item"}:
            prefix = ""
            if typ == "task_list_item":
                prefix = '<input type="checkbox" disabled' + (" checked" if attrs.get("checked") else "") + "> "
            return f"<li>{prefix}{child()}</li>\n"
        if typ == "table": return f"<table>\n{child()}</table>\n"
        if typ == "table_head": return f"<thead>\n<tr>{child()}</tr>\n</thead>\n"
        if typ == "table_body": return f"<tbody>\n{child()}</tbody>\n"
        if typ == "table_row": return f"<tr>{child()}</tr>\n"
        if typ == "table_cell":
            tag = "th" if attrs.get("head") else "td"
            align = attrs.get("align")
            extra = f' style="text-align:{align}"' if align in {"left", "center", "right"} else ""
            return f"<{tag}{extra}>{child()}</{tag}>"
        if typ == "block_code":
            try:
                result = render_fence(t.get("raw", ""), attrs.get("info"), fenced=t.get("style") == "fenced")
            except FenceError as e:
                raise SourceError(e.code, f"Slide {self.slide_number}: {e}") from e
            if result.warning:
                self.deck.warn("W_UNKNOWN_CODE_LANGUAGE", f"Slide {self.slide_number}: {result.warning.split(': ', 1)[-1]}", self.line)
            if result.language: self.deck.languages.add(result.language)
            if result.mermaid: self.deck.has_mermaid = True
            return result.html
        if typ in {"block_html", "inline_html"}:
            return self._render_comment_or_container(t.get("raw", ""))
        raise SourceError("E_MARKDOWN_UNSUPPORTED", f"Slide {self.slide_number}: unsupported Markdown syntax ({typ})")


def parse_deck(source: str, directory: Path) -> Deck:
    deck = Deck()
    try:
        config, body, first_line = frontmatter(source)
        deck.meta = config
        segments = split_slides(body, first_line)
    except SourceError as e:
        deck.error(e.code, str(e), e.line)
        return deck
    parser = mistune.create_markdown(renderer="ast", plugins=["table", "strikethrough", "task_lists", "url"])
    cache: dict[Path, str] = {}
    for slide_no, (segment, line) in enumerate(segments, 1):
        try:
            tokens = parser(segment)
            renderer = HtmlTokens(deck, directory, slide_no, line, cache)
            rendered = renderer.render_many(tokens)
            renderer.finish()
            if not rendered.strip():
                raise SourceError("E_EMPTY_SLIDE", f"Slide {slide_no} contains no renderable content", line)
            deck.slides.append(rendered)
        except SourceError as e:
            deck.error(e.code, str(e), e.line or line)
    return deck
