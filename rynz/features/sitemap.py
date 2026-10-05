"""sitemap.xml listing every indexable page."""

from __future__ import annotations


def register(rynz):
    @rynz.generator
    def sitemap(site, render):
        opts = site.config["sitemap"]
        if not opts.get("enabled"):
            return
        entries = [{"loc": site.url + "/", "lastmod": site.posts[0].last_updated if site.posts else None}]
        entries += [{"loc": p.permalink, "lastmod": p.last_updated} for p in site.pages if not p.noindex]
        entries += site.config.get("_extra_sitemap", [])
        yield opts.get("output", "sitemap.xml"), render("sitemap.xml", entries=entries)
