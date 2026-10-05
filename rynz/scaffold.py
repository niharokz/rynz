"""Commands that create files: `rynz new`, `rynz add`, `rynz init-ci`, `rynz migrate`.

Every file they write comes from rynz/scaffold/ or rynz/ci/ — nothing is hardcoded here.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
from importlib import resources
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rynz import log
from rynz import config as config_mod
from rynz.content import slugify
from rynz.errors import RynzError

CI_TARGETS = {
    "gitlab": [("gitlab-ci.yml", ".gitlab-ci.yml")],
    "cloudflare": [("wrangler.toml", "wrangler.toml"), ("cloudflare-gitlab-ci.yml", ".gitlab-ci.yml")],
    "rsync": [("deploy.sh", "deploy.sh")],
}


def _package_dir(name: str) -> Path:
    return Path(str(resources.files("rynz") / name))


def _render(folder: Path, template: str, **context: object) -> str:
    env = Environment(loader=FileSystemLoader(str(folder)), keep_trailing_newline=True)
    return env.get_template(template).render(**context)


def new_site(target: Path | str, title: str | None = None, url: str = "https://example.com") -> Path:
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise RynzError(f"`{target}` already exists and is not empty")
    source = _package_dir("scaffold") / "project"
    shutil.copytree(source, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.j2", "gitignore", "__pycache__"))
    context = {"title": title or target.name, "url": url.rstrip("/"), "today": dt.date.today().isoformat()}
    for template in source.rglob("*.j2"):
        rel = template.relative_to(source).with_suffix("")
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        (target / rel).write_text(_render(template.parent, template.name, **context), encoding="utf-8")
    shutil.copy(source / "gitignore", target / ".gitignore")
    for folder in ("template", "static", "data"):  # empty on purpose: drop overrides here
        (target / folder).mkdir(exist_ok=True)
    return target


def add_note(title: str, root: Path | str = ".", folder: str | None = None) -> Path:
    root = Path(root)
    cfg = config_mod.load(root, warn_legacy=False)
    slug = slugify(title)
    content = root / cfg.paths["content"]
    target = content / (folder or "note") / f"{slug}.md"
    if target.exists():
        raise RynzError(f"{target.relative_to(root)} already exists — pick another title or edit that file")
    target.parent.mkdir(parents=True, exist_ok=True)
    text = _render(_package_dir("scaffold"), "note.md.j2", title=title, today=dt.date.today().isoformat(),
                   tag=cfg["posts"]["tag"] or "note")
    target.write_text(text, encoding="utf-8")
    return target


def init_ci(kind: str, root: Path | str = ".", force: bool = False) -> list[Path]:
    if kind not in CI_TARGETS:
        raise RynzError(f"unknown CI target `{kind}` (choose from {', '.join(CI_TARGETS)})")
    root = Path(root)
    cfg = config_mod.load(root, warn_legacy=False)
    written = []
    for source_name, target_name in CI_TARGETS[kind]:
        target = root / target_name
        if target.exists() and not force:
            raise RynzError(f"{target_name} already exists — use --force to overwrite it")
        text = _render(_package_dir("ci"), source_name, output=cfg.paths["output"],
                       name=slugify(cfg["title"]), url=cfg["url"])
        target.write_text(text, encoding="utf-8")
        if target_name.endswith(".sh"):
            target.chmod(0o755)
        written.append(target)
    return written


# `rynz migrate` -------------------------------------------------------------

def migrate(root: Path | str = ".", dry_run: bool = False) -> list[str]:
    """Rename rynz 1.x keys in config.yml line by line, so your comments survive."""
    root = Path(root)
    path = root / config_mod.CONFIG_FILE
    if not path.exists():
        raise RynzError("config.yml not found", path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    nested: dict[str, dict[str, str]] = {}
    kept: list[str] = []
    changes: list[str] = []
    key_re = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$")
    for line in lines:
        match = key_re.match(line.rstrip("\n"))
        if match and match.group(1) in config_mod.LEGACY_KEYS:
            old, value = match.group(1), match.group(2)
            new = config_mod.LEGACY_KEYS[old]
            section, _, leaf = new.partition(".")
            if leaf:
                nested.setdefault(section, {})[leaf] = _strip_template_dir(old, value)
            else:
                kept.append(f"{new}: {value}\n")
            changes.append(f"{old} → {new}")
            continue
        kept.append(line)
    if not changes:
        return []
    clash = [s for s in nested if any(re.match(rf"^{re.escape(s)}\s*:", line) for line in kept)]
    if clash:
        raise RynzError(f"config.yml already has a `{clash[0]}:` section — move the old keys into it by hand", path)
    if kept and not kept[-1].endswith("\n"):
        kept[-1] += "\n"
    block = ["\n# Renamed by `rynz migrate` (rynz 2.0 names)\n"]
    for section, values in nested.items():
        block.append(f"{section}:\n")
        block += [f"  {leaf}: {value}\n" for leaf, value in values.items()]
    if not dry_run:
        shutil.copy(path, path.with_suffix(".yml.bak"))
        path.write_text("".join(kept + block), encoding="utf-8")
    return changes


def _strip_template_dir(old: str, value: str) -> str:
    """`template/note_template.html` becomes `note_template.html` (the template folder is searched first)."""
    if old.endswith("_template"):
        clean = value.strip("'\"")
        if clean.startswith("template/"):
            return clean[len("template/"):]
    return value


def ensure_gitignore(root: Path) -> None:
    """Add the incremental-build cache to .gitignore if it isn't there."""
    gi = root / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if ".rynz-cache.json" not in lines:
        gi.write_text("\n".join([*lines, ".rynz-cache.json"]) + "\n", encoding="utf-8")
        log.debug("added .rynz-cache.json to .gitignore")
