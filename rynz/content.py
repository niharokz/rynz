"""Find Markdown files, read their frontmatter, and turn them into Page objects."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rynz import log
from rynz.config import Config
from rynz.errors import ContentError

KNOWN_FIELDS = {
    "title", "description", "subtitle", "date", "updated", "tags", "draft", "slug",
    "template", "image", "aliases", "noindex", "nofeed", "head", "meta", "toc",
}


@dataclass
class Page:
    """One Markdown file and everything rynz knows about it."""

    source: Path
    slug: str
    title: str
    body: str  # Markdown, without frontmatter
    meta: dict[str, Any] = field(default_factory=dict)  # frontmatter exactly as written
    description: str = ""
    date: dt.date | None = None
    updated: dt.date | None = None
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    template: str | None = None
    image: str = ""
    aliases: list[str] = field(default_factory=list)
    noindex: bool = False
    nofeed: bool = False
    head: str = ""
    toc_enabled: bool = False
    # Filled in later by the build
    url: str = ""        # site-relative link, e.g. /notes.html or /notes/
    permalink: str = ""  # absolute URL
    output: str = ""     # path inside the output folder, e.g. notes.html
    html: str = ""
    toc: str = ""
    words: int = 0
    reading_time: int = 0
    prev: "Page | None" = None
    next: "Page | None" = None
    extra: dict[str, Any] = field(default_factory=dict)

    # Lets old templates keep writing `post.title`, `post['url']`, `post.get('subtitle')`
    def __getitem__(self, key: str) -> Any:
        if key == "url":
            return "/" + self.output
        if key == "note":
            return self.html
        if key in self.meta:
            return self.meta[key]
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            value = self[key]
        except AttributeError:
            return default
        return default if value is None else value

    def __contains__(self, key: str) -> bool:
        return key in self.meta or hasattr(self, key)

    @property
    def last_updated(self) -> dt.date | None:
        return self.updated or self.date


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text) or "untitled"


def to_date(value: Any, path: Path, name: str) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise ContentError(f"`{name}` must be a date like 2026-10-05, got {value!r}", path) from exc


def split_frontmatter(text: str, path: Path) -> tuple[dict | None, str]:
    """Return (frontmatter dict or None, body). Frontmatter sits between two `---` lines at the top."""
    text = text.lstrip("﻿")
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.strip()), None)
    if start is None or not lines[start].startswith("---"):
        return None, text
    for end in range(start + 1, len(lines)):
        if lines[end].startswith("---"):
            raw = "".join(lines[start + 1:end])
            try:
                data = yaml.safe_load(raw) or {}
            except yaml.YAMLError as exc:
                mark = getattr(exc, "problem_mark", None)
                line = start + 2 + mark.line if mark else None
                raise ContentError(f"invalid frontmatter: {getattr(exc, 'problem', exc)}", path, line) from exc
            if not isinstance(data, dict):
                raise ContentError("frontmatter must be key: value pairs", path, start + 1)
            return data, "".join(lines[end + 1:])
    raise ContentError("frontmatter starts with --- but never closes", path, start + 1)


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v) for v in value]


def parse_page(path: Path, root: Path) -> Page | None:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text, path)
    if meta is None:
        log.warn(f"{path.relative_to(root)}: no frontmatter, skipped (add --- title: ... --- at the top)")
        return None
    title = meta.get("title")
    if not title:
        heading = re.search(r"^#\s+(.+)$", body, re.M)
        title = heading.group(1).strip() if heading else path.stem
    page = Page(
        source=path,
        slug=str(meta.get("slug") or path.stem),
        title=str(title),
        body=body,
        meta=meta,
        description=str(meta.get("description") or meta.get("subtitle") or ""),
        date=to_date(meta.get("date"), path, "date"),
        updated=to_date(meta.get("updated"), path, "updated"),
        tags=_list(meta.get("tags")),
        draft=bool(meta.get("draft", False)),
        template=meta.get("template"),
        image=str(meta.get("image") or ""),
        aliases=_list(meta.get("aliases")),
        noindex=bool(meta.get("noindex", False)),
        nofeed=bool(meta.get("nofeed", False)),
        head=str(meta.get("head") or meta.get("meta") or ""),
        toc_enabled=bool(meta.get("toc", False)),
        extra={k: v for k, v in meta.items() if k not in KNOWN_FIELDS},
    )
    return page


def discover(cfg: Config, include_drafts: bool = False) -> list[Page]:
    """Every Markdown page under the content folder, except the partials."""
    root = Path(cfg["_root"])
    content = root / cfg.paths["content"]
    if not content.is_dir():
        raise ContentError("content folder not found", content)
    partials = {(root / p).resolve() for p in cfg.partials.values() if p}
    pages: list[Page] = []
    for path in sorted(content.rglob("*.md")):
        if path.resolve() in partials or any(part.startswith((".", "_")) for part in path.relative_to(content).parts):
            continue
        page = parse_page(path, root)
        if page is None:
            continue
        if page.draft and not include_drafts:
            log.debug(f"draft skipped: {path.relative_to(root)}")
            continue
        pages.append(page)
    return pages


def assign_urls(pages: list[Page], cfg: Config) -> None:
    """Decide where each page is written and how it is linked."""
    style = cfg["urls"]
    seen: dict[str, Path] = {}
    for page in pages:
        if page.slug in seen:
            raise ContentError(f"duplicate slug `{page.slug}` (also used by {seen[page.slug]})", page.source)
        seen[page.slug] = page.source
        page.output, page.url = output_for(page.slug, style)
        page.permalink = cfg["url"] + page.url


def output_for(slug: str, style: str) -> tuple[str, str]:
    """(file path inside the output folder, site-relative URL) for a slug."""
    slug = slug.strip("/")
    if style == "pretty":
        return f"{slug}/index.html", f"/{slug}/"
    if style == "clean":
        return f"{slug}.html", f"/{slug}"
    return f"{slug}.html", f"/{slug}.html"
