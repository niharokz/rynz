from __future__ import annotations

import shutil
import textwrap
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"


def write_site(root: Path, config: dict | None = None, files: dict[str, str] | None = None) -> Path:
    """Create a minimal site: config.yml plus the given files (paths relative to root)."""
    cfg = {"title": "Test site", "url": "https://test.example", "theme": "default"}
    cfg.update(config or {})
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.yml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (root / "content").mkdir(exist_ok=True)
    for rel, text in (files or {}).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
    return root


def post(title: str, date: str = "2026-01-01", tags: str = "[note]", body: str = "Hello.", **extra) -> str:
    lines = ["---", f'title: "{title}"', f"date: {date}", f"tags: {tags}"]
    lines += [f"{k}: {v}" for k, v in extra.items()]
    lines += ["---", "", body, ""]
    return "\n".join(lines)


@pytest.fixture
def site(tmp_path: Path):
    def make(config: dict | None = None, files: dict[str, str] | None = None) -> Path:
        return write_site(tmp_path / "site", config, files)

    return make


@pytest.fixture
def legacy_site(tmp_path: Path) -> Path:
    target = tmp_path / "legacy"
    shutil.copytree(FIXTURES / "legacy_site", target)
    return target
