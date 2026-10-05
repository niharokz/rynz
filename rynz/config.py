"""Load, upgrade and validate `config.yml`.

Only `title` and `url` are required; everything else has a default. Keys from
rynz 1.x are still read and mapped to their 2.0 names (see LEGACY_KEYS), and
the original keys stay available to templates (`config.get('desc')` works).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from rynz import log
from rynz.errors import ConfigError

CONFIG_FILE = "config.yml"

DEFAULTS: dict[str, Any] = {
    "title": None,
    "url": None,
    "description": "",
    "author": "",
    "email": "",
    "language": "en",
    "image": "",
    "theme": None,  # None = built-in templates only as a fallback; "default" or a path to use a theme
    "menu": [],
    "footer_menu": [],
    "paths": {
        "content": "content",
        "templates": "template",
        "static": "static",
        "output": "public",
        "data": "data",
    },
    "partials": {
        "home": "content/home.md",
        "header": "content/header.md",
        "footer": "content/footer.md",
    },
    "templates": {
        "home": "home.html",
        "note": "note.html",
        "list": "list.html",
        "trim_blocks": True,  # strip the blank lines Jinja tags leave behind
    },
    "posts": {"tag": "note"},
    "urls": "flat",  # flat: /x.html · clean: file x.html, link /x · pretty: /x/
    "markdown": {
        "extras": [
            "fenced-code-blocks",
            "tables",
            "footnotes",
            "header-ids",
            "cuddled-lists",
            "strike",
            "task_list",
            "toc",
            "code-friendly",
        ],
        "strip_classes": True,
        "lazy_images": True,
        "highlight": {"enabled": True, "style": "monokai"},
    },
    "feed": {
        "enabled": True,
        "output": "rss.xml",
        "template": "feed.xml",
        "limit": 0,
        "full_content": False,
        "tag_feeds": True,
    },
    "sitemap": {"enabled": True, "output": "sitemap.xml"},
    "robots": {"enabled": True, "output": "robots.txt"},
    "tags": {"enabled": False, "path": "tag"},
    "archive": {"enabled": False, "output": "archive"},
    "redirects": {"enabled": True},
    "opml": {"enabled": False, "data": "blogroll", "output": "blogroll.opml"},
    "gemini": {"enabled": False, "output": "gemini"},
    "reading_speed": 200,
    "plugins": [],
}

# rynz 1.x key -> 2.0 dotted key
LEGACY_KEYS: dict[str, str] = {
    "desc": "description",
    "mail": "email",
    "home_path": "paths.output",
    "content_path": "paths.content",
    "resource_path": "paths.static",
    "home_md": "partials.home",
    "header_md": "partials.header",
    "footer_md": "partials.footer",
    "note_template": "templates.note",
    "home_template": "templates.home",
    "feed_template": "feed.template",
}

URL_STYLES = ("flat", "clean", "pretty")


class Config(dict):
    """A dict that also allows `config.paths.output` style access."""

    def __getattr__(self, name: str) -> Any:
        try:
            value = self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
        return Config(value) if isinstance(value, dict) and not isinstance(value, Config) else value

    def dotted(self, key: str, default: Any = None) -> Any:
        node: Any = self
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _set_dotted(data: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    node = data
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _bool_section(raw: dict, name: str) -> None:
    """Allow `feed: false` as shorthand for `feed: {enabled: false}`."""
    if isinstance(raw.get(name), bool):
        raw[name] = {"enabled": raw[name]}


def upgrade_legacy(raw: dict) -> tuple[dict, list[str]]:
    """Map 1.x keys onto 2.0 names. Returns the upgraded dict and the keys mapped."""
    upgraded = copy.deepcopy(raw)
    mapped = []
    for old, new in LEGACY_KEYS.items():
        if old in raw:
            _set_dotted(upgraded, new, raw[old])
            mapped.append(old)
    if mapped and "trim_blocks" not in raw.get("templates", {}):
        _set_dotted(upgraded, "templates.trim_blocks", False)  # keep 1.x whitespace byte for byte
    if "site-title" in raw and "title" not in raw:
        upgraded["title"] = raw["site-title"]
    return upgraded, mapped


def validate(cfg: Config) -> list[str]:
    """Return a list of problems; an empty list means the config is valid."""
    problems = []
    for key in ("title", "url"):
        if not cfg.get(key):
            problems.append(f"`{key}` is required")
    url = cfg.get("url") or ""
    if url and not str(url).startswith(("http://", "https://")):
        problems.append("`url` must start with http:// or https://")
    if cfg.get("urls") not in URL_STYLES:
        problems.append(f"`urls` must be one of: {', '.join(URL_STYLES)}")
    if not isinstance(cfg.get("plugins"), list):
        problems.append("`plugins` must be a list of module names")
    if not isinstance(cfg.dotted("markdown.extras"), (list, dict)):
        problems.append("`markdown.extras` must be a list")
    for key in ("menu", "footer_menu"):
        items = cfg.get(key)
        if not isinstance(items, list) or any(not isinstance(i, dict) or "url" not in i for i in items):
            problems.append(f"`{key}` must be a list of {{name, url}} items")
    return problems


def load(root: Path | str = ".", warn_legacy: bool = True) -> Config:
    """Read `config.yml` from `root`, apply defaults and legacy mapping, validate."""
    root = Path(root)
    path = root / CONFIG_FILE
    if not path.exists():
        raise ConfigError("config.yml not found — run `rynz new <folder>` to start a site", path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        line = getattr(getattr(exc, "problem_mark", None), "line", None)
        raise ConfigError(f"invalid YAML: {exc}", path, (line + 1) if line is not None else None) from exc
    if not isinstance(raw, dict):
        raise ConfigError("must be a mapping of keys to values", path)

    for section in ("feed", "sitemap", "robots", "tags", "archive", "redirects", "opml", "gemini"):
        _bool_section(raw, section)
    if isinstance(raw.get("markdown", {}).get("highlight"), bool):
        raw["markdown"]["highlight"] = {"enabled": raw["markdown"]["highlight"]}

    upgraded, mapped = upgrade_legacy(raw)
    if mapped and warn_legacy:
        names = ", ".join(f"{k} → {LEGACY_KEYS[k]}" for k in mapped)
        log.warn(f"config.yml uses rynz 1.x keys ({names}). They still work; `rynz migrate` renames them.")

    cfg = Config(_merge(DEFAULTS, upgraded))
    cfg["url"] = str(cfg.get("url") or "").rstrip("/")
    cfg["_root"] = str(root.resolve())
    cfg["_legacy"] = bool(mapped)

    problems = validate(cfg)
    if problems:
        raise ConfigError("; ".join(problems), path)
    return cfg


def public_view(cfg: Config) -> dict:
    """The config without internal keys, for printing."""
    return {k: v for k, v in cfg.items() if not k.startswith("_")}
