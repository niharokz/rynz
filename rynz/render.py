"""Jinja2 setup: where templates are looked up, filters, and page context."""

from __future__ import annotations

import datetime as dt
import email.utils
from importlib import resources
from pathlib import Path
from typing import Any, Callable
from xml.sax.saxutils import escape

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined, Undefined, select_autoescape

from rynz.config import Config
from rynz.content import Page
from rynz.errors import ConfigError


def builtin_theme_dir(name: str = "default") -> Path:
    return Path(str(resources.files("rynz") / "themes" / name))


def theme_dir(cfg: Config) -> Path | None:
    """The folder of the theme named in config, or None if no theme is set."""
    theme = cfg.get("theme")
    if not theme:
        return None
    builtin = builtin_theme_dir(str(theme))
    if builtin.is_dir():
        return builtin
    path = Path(cfg["_root"]) / str(theme)
    if path.is_dir():
        return path
    raise ConfigError(f"theme `{theme}` not found (built-in name or folder path)")


def template_dirs(cfg: Config) -> list[Path]:
    """Lookup order: your template folder, the configured theme, rynz's built-in theme, the project root."""
    root = Path(cfg["_root"])
    dirs = [root / cfg.paths["templates"]]
    theme = theme_dir(cfg)
    if theme:
        dirs.append(theme / "templates")
    dirs.append(builtin_theme_dir() / "templates")
    dirs.append(root)  # rynz 1.x config names templates by path, e.g. template/note_template.html
    seen, unique = set(), []
    for d in dirs:
        if d.resolve() not in seen and d.is_dir():
            seen.add(d.resolve())
            unique.append(d)
    return unique


def _to_date(value: Any) -> dt.date | dt.datetime | None:
    if isinstance(value, (dt.date, dt.datetime)):
        return value
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def f_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    d = _to_date(value)
    return d.strftime(fmt) if d else ""


def f_rfc822(value: Any) -> str:
    d = _to_date(value)
    if d is None:
        return ""
    if not isinstance(d, dt.datetime):
        d = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)
    return email.utils.format_datetime(d.astimezone(dt.timezone.utc), usegmt=True)


def f_iso(value: Any) -> str:
    d = _to_date(value)
    return d.isoformat() if d else ""


class Templates:
    def __init__(self, cfg: Config, filters: dict[str, Callable] | None = None, strict: bool = False):
        self.cfg = cfg
        self.dirs = template_dirs(cfg)
        trim = bool(cfg["templates"].get("trim_blocks", True))
        self.env = Environment(
            loader=ChoiceLoader([FileSystemLoader(str(d)) for d in self.dirs]),
            autoescape=select_autoescape(enabled_extensions=(), default_for_string=False, default=False),
            undefined=StrictUndefined if strict else Undefined,
            # rynz 1.x projects get Jinja's defaults so their output stays byte for byte the same
            keep_trailing_newline=trim,
            trim_blocks=trim,
            lstrip_blocks=trim,
        )
        base = cfg["url"]
        self.env.filters.update(
            date=f_date,
            rfc822=f_rfc822,
            iso=f_iso,
            xml=lambda s: escape(str(s or "")),
            absolute_url=lambda path: base + "/" + str(path or "").lstrip("/"),
        )
        self.env.filters.update(filters or {})

    def exists(self, name: str) -> bool:
        try:
            self.env.get_template(name)
            return True
        except Exception:
            return False

    def render(self, name: str, **context: Any) -> str:
        return self.env.get_template(name).render(**context)

    def files(self) -> list[Path]:
        """Every template file in the lookup chain (used for incremental builds)."""
        out = []
        for d in self.dirs[:-1]:  # skip the project-root fallback
            out += [p for p in d.rglob("*") if p.is_file()]
        return out


def page_context(site: Any, page: Page, **extra: Any) -> dict[str, Any]:
    """Variables every page template gets. New names first, then the rynz 1.x names."""
    cfg = site.config
    legacy_posts = extra.pop("legacy_posts", "")
    ctx: dict[str, Any] = {
        "site": site,
        "page": page,
        "config": cfg,
        "content": page.html,
        "toc": page.toc,
        # rynz 1.x names, kept so old templates render unchanged
        "title": cfg["title"],
        "post_title": page.title if page.slug != "index" else "",
        "post_subtitle": page.description if page.slug != "index" else "",
        "date": page.date if page.slug != "index" else "",
        "metad": page.head if page.slug != "index" else "",
        "url": cfg["url"] + "/" + page.output,
        "article": page.html,
        "posts": legacy_posts,
        "home": cfg["partials"]["home"],
        "header": site.header,
        "footer": site.footer,
        "last_date": "",
    }
    ctx.update(extra)
    return ctx
