"""The one place Markdown becomes HTML.

markdown2 does the conversion with extras on. Afterwards rynz:
- highlights fenced code with Pygments using inline styles (no classes, no JavaScript),
- removes the class attributes markdown2 adds (footnotes, task lists), unless turned off,
- adds loading="lazy" and width/height to local images.
"""

from __future__ import annotations

import html as htmllib
import re
import struct
from pathlib import Path

import markdown2

from rynz.config import Config

_CODE_RE = re.compile(r'<pre><code class="([\w+-]+) language-[\w+-]+">(.*?)</code></pre>', re.S)
_CLASS_RE = re.compile(r'\s+class="[^"]*"')
_IMG_RE = re.compile(r"<img\b([^>]*?)\s*/?>")
_ATTR_RE = re.compile(r'(\w[\w-]*)="([^"]*)"')


class Renderer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        md = cfg["markdown"]
        extras = md.get("extras") or []
        extras = dict(extras) if isinstance(extras, dict) else {name: None for name in extras}
        # markdown2 would call Pygments itself and emit CSS classes. This extra makes it
        # leave code blocks plain (tagged with the language) so rynz can highlight them.
        extras.setdefault("highlightjs-lang", None)
        self.extras = extras
        self.highlight = md.get("highlight") or {}
        self.strip_classes = md.get("strip_classes", True)
        self.lazy_images = md.get("lazy_images", True)
        self.root = Path(cfg["_root"])
        self.static = self.root / cfg.paths["static"]

    def render(self, text: str, source: Path | None = None) -> tuple[str, str]:
        """Return (html, table_of_contents_html)."""
        result = markdown2.markdown(text, extras=self.extras)
        toc = getattr(result, "toc_html", None) or ""
        out = str(result)
        out = _CODE_RE.sub(self._code_block, out)
        if self.strip_classes:
            out = _CLASS_RE.sub("", out)
            toc = _CLASS_RE.sub("", toc)
        if self.lazy_images:
            out = _IMG_RE.sub(lambda m: self._image(m, source), out)
        return out, toc

    # Code highlighting --------------------------------------------------
    def _code_block(self, match: re.Match) -> str:
        lang, code = match.group(1), htmllib.unescape(match.group(2)).rstrip("\n")
        if not self.highlight.get("enabled", True):
            return f"<pre><code>{htmllib.escape(code, quote=False)}</code></pre>"
        try:
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_by_name
            from pygments.util import ClassNotFound
        except ImportError:  # pragma: no cover - Pygments is a dependency
            return f"<pre><code>{htmllib.escape(code, quote=False)}</code></pre>"
        try:
            lexer = get_lexer_by_name(lang)
        except ClassNotFound:
            return f"<pre><code>{htmllib.escape(code, quote=False)}</code></pre>"
        style = self.highlight.get("style", "monokai")
        formatter = HtmlFormatter(nowrap=True, noclasses=True, style=style)
        body = highlight(code, lexer, formatter).rstrip("\n")
        return f'<pre style="{_pre_style(style)}"><code>{body}</code></pre>'

    # Images -------------------------------------------------------------
    def _image(self, match: re.Match, source: Path | None) -> str:
        attrs = dict(_ATTR_RE.findall(match.group(1)))
        if "loading" not in attrs:
            attrs["loading"] = "lazy"
        if "width" not in attrs and "height" not in attrs:
            size = image_size(self._find(attrs.get("src", ""), source))
            if size:
                attrs["width"], attrs["height"] = str(size[0]), str(size[1])
        rendered = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f"<img {rendered}>"

    def _find(self, src: str, source: Path | None) -> Path | None:
        if not src or "://" in src or src.startswith(("data:", "//")):
            return None
        src = src.split("?")[0].split("#")[0]
        candidates = []
        if src.startswith("/"):
            candidates += [self.static / src.lstrip("/"), self.root / src.lstrip("/")]
        else:
            if source:
                candidates.append(source.parent / src)
            candidates.append(self.static / src)
        return next((c for c in candidates if c.is_file()), None)


def _pre_style(name: str) -> str:
    """Background and text colour of a Pygments style, so highlighted code stays readable in light and dark themes."""
    from pygments.styles import get_style_by_name
    from pygments.token import Text

    style = get_style_by_name(name)
    text = style.style_for_token(Text).get("color") or ""
    return f"background:{style.background_color}" + (f";color:#{text}" if text else "")


def image_size(path: Path | None) -> tuple[int, int] | None:
    """Read width and height from PNG, GIF, JPEG or WebP headers (no Pillow needed)."""
    if not path:
        return None
    try:
        with path.open("rb") as f:
            head = f.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                chunk = head[12:16]
                if chunk == b"VP8X":
                    return int.from_bytes(head[24:27], "little") + 1, int.from_bytes(head[27:30], "little") + 1
                if chunk == b"VP8 ":
                    w, h = struct.unpack("<HH", head[26:30])
                    return w & 0x3FFF, h & 0x3FFF
                if chunk == b"VP8L":
                    bits = int.from_bytes(head[21:25], "little")
                    return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(3)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    length = struct.unpack(">H", f.read(2))[0]
                    f.seek(length - 2, 1)
    except (OSError, struct.error):
        return None
    return None


def word_count(markdown_text: str) -> int:
    text = re.sub(r"```.*?```", " ", markdown_text, flags=re.S)
    return len(re.findall(r"\w+", text))
