import re
from pathlib import Path

import pytest
import yaml

from rynz import config
from rynz.checks import check_site
from rynz.cli import main
from rynz.scaffold import migrate
from tests.conftest import post

ROOT = Path(__file__).parent.parent


def test_new_add_build_check(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "blog", "--title", "My blog", "--url", "https://blog.example"]) == 0
    assert (tmp_path / "blog" / ".gitignore").exists()
    assert main(["-C", "blog", "add", "First post!"]) == 0
    note = tmp_path / "blog" / "content" / "note" / "first-post.md"
    assert 'title: "First post!"' in note.read_text()
    assert main(["-C", "blog", "add", "First post!"]) == 1  # refuses to overwrite (1.0.1 bug)
    assert main(["-C", "blog", "build", "--check"]) == 0
    assert (tmp_path / "blog" / "public" / "hello-world.html").exists()
    assert not (tmp_path / "blog" / "public" / "first-post.html").exists()  # still a draft


def test_old_command_names_still_work(site, capsys):
    root = site(files={"content/a.md": post("A")})
    assert main(["-C", str(root), "deploy"]) == 0
    assert "is now `rynz build`" in capsys.readouterr().err
    assert main(["-C", str(root), "test"]) == 0


def test_save_is_gone(capsys):
    assert main(["save"]) == 2
    assert "removed" in capsys.readouterr().err


def test_config_command_validates(site, capsys):
    root = site()
    assert main(["-C", str(root), "config"]) == 0
    assert "paths:" in capsys.readouterr().out
    (root / "config.yml").write_text("title: x\nurl: nope\n")
    assert main(["-C", str(root), "config"]) == 1


def test_check_finds_broken_links_and_missing_alt(site):
    root = site(files={"content/a.md": post("A", body="[gone](/nope.html) [ok](/) ![](/x.png)\n\n[here](#missing)")})
    main(["-C", str(root), "build"])
    report = check_site(root / "public", "https://test.example")
    messages = [i.message for i in report.issues]
    assert "broken link: /nope.html" in messages
    assert "anchor #missing not found on this page" in messages
    assert any("without alt" in m for m in messages)
    assert main(["-C", str(root), "check"]) == 1


def test_migrate_keeps_comments_and_builds_the_same(legacy_site):
    text = (legacy_site / "config.yml").read_text()
    changes = migrate(legacy_site)
    assert "home_path → paths.output" in changes
    new = (legacy_site / "config.yml").read_text()
    assert "# Optional Configuration" in new and "home_path" not in new
    assert (legacy_site / "config.yml.bak").read_text() == text
    data = yaml.safe_load(new)
    assert data["templates"]["note"] == "note_template.html"
    cfg = config.load(legacy_site)
    assert cfg.paths.output == "public" and not cfg["_legacy"]
    assert migrate(legacy_site) == []


def test_init_ci(site):
    root = site()
    assert main(["-C", str(root), "init-ci", "gitlab"]) == 0
    assert "rynz build --check" in (root / ".gitlab-ci.yml").read_text()
    assert main(["-C", str(root), "init-ci", "gitlab"]) == 1  # won't overwrite without --force
    assert main(["-C", str(root), "init-ci", "rsync"]) == 0
    assert 'rsync -az --delete "public/"' in (root / "deploy.sh").read_text()


def test_no_html_css_or_yaml_strings_in_python_code():
    """Templates, CSS and starter files live in folders, never inside .py files."""
    pattern = re.compile(r"<!DOCTYPE|<html|<\?xml|<head>|<body|\{\s*margin|---\\ntitle:", re.I)
    offenders = []
    for path in (ROOT / "rynz").rglob("*.py"):
        code = path.read_text(encoding="utf-8")
        code = re.sub(r'(?s)^""".*?"""', "", code)  # module docstrings may show examples
        if pattern.search(code):
            offenders.append(path.name)
    assert offenders == []


def test_readme_examples_are_valid():
    """Every ```yaml block in the README is a valid config (merged onto title/url), and every command exists."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)```", readme, re.S)
    assert blocks, "README should show config examples"
    for block in blocks:
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "title" in data:
            merged = config.Config(config._merge(config.DEFAULTS, data))
            merged["url"] = merged["url"] or "https://x.example"
            assert config.validate(merged) == [], block
    shell = "\n".join(re.findall(r"```bash\n(.*?)```", readme, re.S))
    commands = set(re.findall(r"^rynz ([a-z][a-z-]*)", shell, re.M)) | set(re.findall(r"`rynz ([a-z][a-z-]*)", readme))
    from rynz.cli import _parser

    known = set(_parser()._subparsers._group_actions[0].choices) | {"save"}  # `save` is mentioned as removed
    assert commands <= known, commands - known
