"""The site model templates and plugins work with."""

from __future__ import annotations

import datetime as dt
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rynz import __version__
from rynz.config import Config
from rynz.content import Page, slugify
from rynz.errors import ContentError


@dataclass
class Site:
    config: Config
    pages: list[Page]                       # every page, newest first
    posts: list[Page] = field(default_factory=list)   # pages carrying the posts tag
    tags: "OrderedDict[str, list[Page]]" = field(default_factory=OrderedDict)
    years: "OrderedDict[int, list[Page]]" = field(default_factory=OrderedDict)
    data: dict[str, Any] = field(default_factory=dict)
    header: str = ""                         # rendered content/header.md
    footer: str = ""                         # rendered content/footer.md
    home: str = ""                           # rendered content/home.md
    built: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    generator: str = f"rynz {__version__}"

    @property
    def title(self) -> str:
        return self.config["title"]

    @property
    def url(self) -> str:
        return self.config["url"]

    def page(self, slug: str) -> Page | None:
        return next((p for p in self.pages if p.slug == slug), None)

    def tag_url(self, tag: str) -> str:
        from rynz.content import output_for

        return output_for(f"{self.config['tags']['path']}/{slugify(tag)}", self.config["urls"])[1]


def _sort_key(page: Page) -> tuple:
    return (page.date or dt.date.min, page.title)


def build_site(cfg: Config, pages: list[Page]) -> Site:
    pages = sorted(pages, key=_sort_key, reverse=True)
    tag = cfg["posts"]["tag"]
    posts = [p for p in pages if tag in p.tags] if tag else list(pages)
    for i, post in enumerate(posts):
        post.next = posts[i - 1] if i > 0 else None       # newer
        post.prev = posts[i + 1] if i + 1 < len(posts) else None  # older
    tags: OrderedDict[str, list[Page]] = OrderedDict()
    for name in sorted({t for p in pages for t in p.tags if t != tag}, key=str.lower):
        tags[name] = [p for p in pages if name in p.tags]
    years: OrderedDict[int, list[Page]] = OrderedDict()
    for post in posts:
        if post.date:
            years.setdefault(post.date.year, []).append(post)
    return Site(config=cfg, pages=pages, posts=posts, tags=tags, years=years, data=load_data(cfg))


def load_data(cfg: Config) -> dict[str, Any]:
    """Every data/*.yml file, available as site.data.<name>."""
    folder = Path(cfg["_root"]) / cfg.paths["data"]
    data: dict[str, Any] = {}
    if not folder.is_dir():
        return data
    for path in sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")]):
        try:
            data[path.stem] = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ContentError(f"invalid YAML: {exc}", path) from exc
    return data
