# Contributing to rynz

Thanks for helping. rynz stays small on purpose, so the best changes are ones that make it simpler or fix something.

## Set up

```bash
git clone https://gitlab.com/niharokz/rynz.git
cd rynz
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Where things live

| Path | What it is |
| --- | --- |
| `rynz/cli.py` | Command line; calls the other modules |
| `rynz/config.py` | Loading, defaults, 1.x key mapping, validation |
| `rynz/content.py` | Finding Markdown files and reading frontmatter |
| `rynz/markdown.py` | Markdown to HTML, highlighting, images |
| `rynz/site.py` | Posts, tags, years, data files |
| `rynz/render.py` | Jinja2 setup and template lookup |
| `rynz/build.py` | The build pipeline and writing files |
| `rynz/plugins.py` | The plugin API |
| `rynz/features/` | Built-in features, written as plugins |
| `rynz/checks.py`, `server.py`, `scaffold.py` | `check`, `serve`, and `new`/`add`/`migrate`/`init-ci` |
| `rynz/themes/default/` | Default templates and nss.css |
| `rynz/scaffold/`, `rynz/ci/` | Files copied by `new`, `add` and `init-ci` |

## Rules

- No HTML, CSS, XML or YAML inside `.py` files; put them in a folder and load them. A test enforces this.
- Output stays JavaScript-free.
- Every change comes with a test. Run `pytest` before you push.
- Keep the README true: its config examples and commands are tested.

## Releasing

1. Bump `__version__` in `rynz/__init__.py` and add a CHANGELOG entry.
2. Push to `master`. CI runs the tests on every supported Python, then uploads to PyPI (skipped if that version already exists).
