"""robots.txt that points search engines at the sitemap."""

from __future__ import annotations


def register(rynz):
    @rynz.generator
    def robots(site, render):
        cfg = site.config
        if not cfg["robots"].get("enabled"):
            return
        sitemap = f"{cfg['url']}/{cfg['sitemap']['output']}" if cfg["sitemap"].get("enabled") else ""
        yield cfg["robots"].get("output", "robots.txt"), render("robots.txt", sitemap_url=sitemap)
