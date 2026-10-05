"""The plugin API.

A plugin is a Python module (or a .py file in your project) with a
`register(rynz)` function. Built-in features use the same API.

    def register(rynz):
        @rynz.hook("html")
        def shout(html, page, site):
            return html.replace("TODO", "<mark>TODO</mark>")

        @rynz.generator
        def humans(site, render):
            yield "humans.txt", f"Site by {site.config['author']}\\n"

        @rynz.filter("shout")
        def shout_filter(text):
            return text.upper()

Hooks, in the order they run:
    config(config)                   after config.yml is loaded
    page(page, site)                 after frontmatter is read, before Markdown
    html(html, page, site) -> str    after Markdown is rendered; return the new HTML
    site(site)                       after collections (posts, tags) are built
    context(context, page, site)     before a page template renders; edit the dict
    done(site, written)              after every file is written
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from typing import Any, Callable, Iterable

from rynz.errors import ConfigError

HOOKS = ("config", "page", "html", "site", "context", "done")

BUILTIN_PLUGINS = (
    "rynz.features.feed",
    "rynz.features.sitemap",
    "rynz.features.robots",
    "rynz.features.tags",
    "rynz.features.archive",
    "rynz.features.redirects",
    "rynz.features.opml",
    "rynz.features.gemini",
)

Generator = Callable[[Any, Callable[..., str]], Iterable[tuple[str, "str | bytes"]]]


class PluginAPI:
    """What `register(rynz)` receives."""

    def __init__(self) -> None:
        self.hooks: dict[str, list[Callable]] = {name: [] for name in HOOKS}
        self.generators: list[tuple[str, Generator]] = []
        self.filters: dict[str, Callable] = {}
        self._current = "?"

    def hook(self, name: str) -> Callable[[Callable], Callable]:
        if name not in HOOKS:
            raise ConfigError(f"plugin {self._current}: unknown hook `{name}` (choose from {', '.join(HOOKS)})")

        def decorator(fn: Callable) -> Callable:
            self.hooks[name].append(fn)
            return fn

        return decorator

    def generator(self, fn: Generator) -> Generator:
        self.generators.append((self._current, fn))
        return fn

    def filter(self, name: str) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable) -> Callable:
            self.filters[name] = fn
            return fn

        return decorator

    # Used by the build ---------------------------------------------------
    def run(self, name: str, *args: Any) -> None:
        for fn in self.hooks[name]:
            fn(*args)

    def run_html(self, html: str, page: Any, site: Any) -> str:
        for fn in self.hooks["html"]:
            result = fn(html, page, site)
            if result is not None:
                html = result
        return html


def _import(name: str, root: Path):
    if name.endswith(".py") or "/" in name or "\\" in name:
        path = (root / name).resolve()
        if not path.is_file():
            raise ConfigError(f"plugin file not found: {name}", root / "config.yml")
        spec = importlib.util.spec_from_file_location(f"rynz_user_plugin_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        return module
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise ConfigError(f"cannot import plugin `{name}`: {exc}", root / "config.yml") from exc


def load_plugins(cfg: dict) -> PluginAPI:
    api = PluginAPI()
    root = Path(cfg["_root"])
    for name in (*BUILTIN_PLUGINS, *cfg.get("plugins", [])):
        module = _import(name, root)
        register = getattr(module, "register", None)
        if not callable(register):
            raise ConfigError(f"plugin `{name}` has no register(rynz) function", root / "config.yml")
        api._current = name
        register(api)
    api._current = "?"
    return api
