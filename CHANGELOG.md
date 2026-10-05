# Changelog

## 2.0.0 — unreleased

A rewrite of rynz's internals. Sites built with 1.x keep working; see "Upgrading from rynz 1.x" in the README.

### Added
- Markdown extras on by default: tables, footnotes, fenced code, heading ids, task lists, strikethrough, lists right after a bold line.
- Code highlighting with Pygments as inline styles (no classes, no JavaScript); `markdown.highlight`.
- Frontmatter: `draft`, `updated`, `slug`, `template`, `image`, `aliases`, `noindex`, `nofeed`, `toc`, `head`; unknown fields kept as `page.extra`.
- Pages at any folder depth under `content/`.
- `sitemap.xml`, `robots.txt`, canonical URLs, Open Graph and Twitter tags in the default theme.
- Tag pages, per-tag feeds, a yearly archive, redirect pages for `aliases`, an OPML blogroll and Gemini capsule output.
- Data files: `data/*.yml` as `site.data`.
- Reading time, previous/next links and an optional table of contents.
- Lazy-loaded images with width and height read from the file.
- URL styles: `flat`, `clean`, `pretty`.
- A public plugin API (`register(rynz)`, six hooks, generators, filters). Built-in features use it.
- `rynz check`, `rynz migrate`, `rynz init-ci`, `rynz build --incremental`, `rynz serve --port` with clean URLs and rebuild on save, `python -m rynz`.
- A default theme (templates and nss.css) shipped as real files.
- Tests, including a byte-for-byte comparison against rynz 1.0.1 output.

### Changed
- Commands renamed: `create` → `new`, `deploy` → `build`, `test` → `check`. Old names still work in 2.0.
- `rynz config` now prints the resolved config and validates it, instead of editing it interactively.
- Config keys renamed (old names still read): `desc` → `description`, `mail` → `email`, `home_path` → `paths.output`, `content_path` → `paths.content`, `resource_path` → `paths.static`, `home_md`/`header_md`/`footer_md` → `partials.*`, `note_template`/`home_template` → `templates.*`, `feed_template` → `feed.template`.
- The feed's channel description is filled from `description`; its date comes from the newest post in the feed.
- Requires Python 3.10 or newer. Packaged with `pyproject.toml`; Pygments added as a dependency.

### Removed
- `rynz save`. Use git directly.

### Fixed
- Errors no longer pass silently: every problem names its file (and line), and the build exits non-zero.
- URLs built on Windows no longer contain backslashes.
- `rynz add` no longer overwrites an existing post.
- The output folder can't be set to a path whose deletion would remove your site's source.
- A site with no posts no longer crashes the feed.
- Templates are loaded once per build instead of once per page.

## 1.0.1 — 2025-04-29
- GitLab CI publishing to PyPI.

## 1.0.0 — 2025-04
- CLI commands `create`, `add`, `deploy`, `serve`, `config`, `test`, `save`.

## 0.9.9 (beta)
- Tag-based homepage visibility replaced `showInHome`.
