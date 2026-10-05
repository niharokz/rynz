"""Redirect pages for old URLs listed in a page's `aliases:` (HTML only, no JavaScript)."""

from __future__ import annotations


def register(rynz):
    @rynz.generator
    def redirects(site, render):
        cfg = site.config
        if not cfg["redirects"].get("enabled"):
            return
        for page in site.pages:
            for alias in page.aliases:
                yield alias_path(alias, cfg["urls"]), render("redirect.html", page=page, target=page.permalink)


def alias_path(alias: str, style: str) -> str:
    alias = alias.strip().strip("/")
    if alias.endswith(".html"):
        return alias
    return f"{alias}/index.html" if style == "pretty" else f"{alias}.html"
