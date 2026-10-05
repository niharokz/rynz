"""Run the pipeline: config → pages → Markdown → site → templates → files."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from rynz import __version__, log
from rynz import config as config_mod
from rynz.config import Config
from rynz.content import Page, assign_urls, discover
from rynz.errors import BuildError, RynzError
from rynz.markdown import Renderer, word_count
from rynz.plugins import load_plugins
from rynz.render import Templates, page_context, theme_dir
from rynz.site import Site, build_site

CACHE_FILE = ".rynz-cache.json"


@dataclass
class BuildResult:
    site: Site
    written: list[str] = field(default_factory=list)
    skipped: int = 0
    seconds: float = 0.0


def safe_output_dir(cfg: Config) -> Path:
    """The output folder, refusing anything a wipe could hurt."""
    root = Path(cfg["_root"]).resolve()
    out = (root / cfg.paths["output"]).resolve()
    if out == root or root.is_relative_to(out):
        raise RynzError(f"output folder `{cfg.paths['output']}` is the project itself — refusing to delete it")
    if not out.is_relative_to(root):
        raise RynzError(f"output folder `{cfg.paths['output']}` is outside the project — refusing to write there")
    if (out / config_mod.CONFIG_FILE).exists():
        raise RynzError(f"output folder `{cfg.paths['output']}` contains config.yml — refusing to delete it")
    for key in ("content", "templates", "static", "data"):
        src = (root / cfg.paths[key]).resolve()
        if src == out or src.is_relative_to(out):
            raise RynzError(f"output folder would delete your `{key}` folder — choose a different paths.output")
    return out


def _digest(*parts: object) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part if isinstance(part, bytes) else str(part).encode())
        h.update(b"\0")
    return h.hexdigest()


def _files_digest(paths: list[Path]) -> str:
    return _digest(*(f"{p}:{p.stat().st_mtime_ns}:{p.stat().st_size}" for p in sorted(paths) if p.exists()))


class Builder:
    def __init__(self, root: Path | str = ".", drafts: bool = False, incremental: bool = False,
                 output: str | None = None):
        self.root = Path(root).resolve()
        self.drafts = drafts
        self.incremental = incremental
        self.output_override = output
        self.errors: list[RynzError] = []

    # The pipeline --------------------------------------------------------
    def build(self) -> BuildResult:
        start = time.perf_counter()
        cfg = config_mod.load(self.root)
        if self.output_override:
            cfg["paths"]["output"] = self.output_override
        out = safe_output_dir(cfg)
        plugins = load_plugins(cfg)
        plugins.run("config", cfg)

        md = Renderer(cfg)
        pages = discover(cfg, include_drafts=self.drafts)
        assign_urls(pages, cfg)

        site = build_site(cfg, pages)
        site.header, site.footer, site.home = (self._partial(md, cfg, k) for k in ("header", "footer", "home"))
        for page in site.pages:
            try:
                plugins.run("page", page, site)
                html, toc = md.render(page.body, page.source)
                page.html = plugins.run_html(html, page, site)
                page.toc = toc if page.toc_enabled else ""
                page.words = word_count(page.body)
                page.reading_time = max(1, math.ceil(page.words / cfg["reading_speed"]))
            except RynzError as exc:
                self.errors.append(exc)
            except Exception as exc:  # a plugin or markdown bug: report it with the file
                self.errors.append(RynzError(f"{type(exc).__name__}: {exc}", page.source))
        plugins.run("site", site)

        templates = Templates(cfg, plugins.filters)
        files: dict[str, str | bytes] = {}
        cache_old = self._read_cache() if self.incremental else {}
        cache_new: dict[str, str] = {}
        shared = _digest(__version__, json.dumps(config_mod.public_view(cfg), default=str, sort_keys=True),
                         _files_digest(templates.files()), site.header, site.footer)
        skipped = 0

        for page in site.pages:
            key = _digest(shared, page.source.read_text(encoding="utf-8"), page.output,
                          page.prev and page.prev.slug, page.next and page.next.slug)
            cache_new[page.output] = key
            if self.incremental and cache_old.get(page.output) == key and (out / page.output).exists():
                skipped += 1
                continue
            name = page.template or cfg["templates"]["note"]
            files[page.output] = self._render(templates, name, site, page, plugins)

        index = self._index_page(site, cfg)
        legacy_posts = list(site.pages)
        files[index.output] = self._render(templates, cfg["templates"]["home"], site, index, plugins,
                                           legacy_posts=legacy_posts)

        def render(name: str, **context: object) -> str:
            return templates.render(name, site=site, config=cfg, **context)

        for plugin_name, generator in plugins.generators:
            try:
                for path, content in generator(site, render) or ():
                    files[self._clean_path(path, plugin_name)] = content
            except RynzError as exc:
                self.errors.append(exc)
            except Exception as exc:
                self.errors.append(RynzError(f"plugin {plugin_name} failed: {type(exc).__name__}: {exc}"))

        if self.errors:
            raise BuildError(self.errors)

        written = self._write(cfg, out, files, cache_old, cache_new)
        plugins.run("done", site, written)
        return BuildResult(site=site, written=written, skipped=skipped, seconds=time.perf_counter() - start)

    # Helpers -------------------------------------------------------------
    def _partial(self, md: Renderer, cfg: Config, name: str) -> str:
        rel = cfg["partials"].get(name)
        path = self.root / rel if rel else None
        if not path or not path.is_file():
            return ""
        return md.render(path.read_text(encoding="utf-8"), path)[0]

    def _index_page(self, site: Site, cfg: Config) -> Page:
        home = self.root / (cfg["partials"].get("home") or "content/home.md")
        page = Page(source=home, slug="index", title=cfg["title"], body="", description=cfg["description"])
        page.output, page.url, page.permalink = "index.html", "/", cfg["url"] + "/"
        page.html = site.home
        return page

    def _render(self, templates: Templates, name: str, site: Site, page: Page, plugins, **extra) -> str:
        try:
            ctx = page_context(site, page, **extra)
            plugins.run("context", ctx, page, site)
            return templates.render(name, **ctx)
        except RynzError as exc:
            self.errors.append(exc)
        except Exception as exc:
            lineno = getattr(exc, "lineno", None)
            where = getattr(exc, "filename", None) or name
            self.errors.append(RynzError(f"template error rendering {page.source.name}: {exc}", where, lineno))
        return ""

    @staticmethod
    def _clean_path(path: str, plugin: str) -> str:
        p = PurePosixPath(str(path).replace("\\", "/").lstrip("/"))
        if ".." in p.parts or not p.parts:
            raise RynzError(f"plugin {plugin} tried to write outside the output folder: {path}")
        return str(p)

    def _read_cache(self) -> dict[str, str]:
        try:
            return json.loads((self.root / CACHE_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, cfg: Config, out: Path, files: dict, cache_old: dict, cache_new: dict) -> list[str]:
        if out.exists() and not self.incremental:
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)

        # Static files: theme first, your static folder on top
        theme = theme_dir(cfg)
        sources = [theme / "static"] if theme else []
        sources.append(self.root / cfg.paths["static"])
        for src in sources:
            if src.is_dir():
                shutil.copytree(src, out, dirs_exist_ok=True)

        written = []
        for rel, content in sorted(files.items()):
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = content.encode("utf-8") if isinstance(content, str) else content
            if self.incremental and target.exists() and target.read_bytes() == data:
                continue
            target.write_bytes(data)
            written.append(rel)

        if self.incremental:
            for stale in set(cache_old) - set(cache_new):
                (out / stale).unlink(missing_ok=True)
        (self.root / CACHE_FILE).write_text(json.dumps(cache_new, indent=0), encoding="utf-8")
        return written


def build(root: Path | str = ".", **options) -> BuildResult:
    return Builder(root, **options).build()


def report(result: BuildResult) -> None:
    site = result.site
    log.ok(
        f"built {len(site.pages)} pages ({len(site.posts)} posts) → {site.config.paths['output']}/ "
        f"in {result.seconds:.2f}s"
        + (f", {result.skipped} unchanged" if result.skipped else "")
    )
