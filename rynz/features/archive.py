"""An archive page with every post grouped by year."""

from __future__ import annotations

from rynz.content import Page, output_for


def register(rynz):
    @rynz.hook("site")
    def add_to_sitemap(site):
        cfg = site.config
        if cfg["archive"].get("enabled"):
            url = output_for(cfg["archive"].get("output", "archive"), cfg["urls"])[1]
            cfg.setdefault("_extra_sitemap", []).append({"loc": site.url + url, "lastmod": None})

    @rynz.generator
    def archive(site, render):
        cfg = site.config
        if not cfg["archive"].get("enabled"):
            return
        output, url = output_for(cfg["archive"].get("output", "archive"), cfg["urls"])
        page = Page(source=cfg["_root"], slug="archive", title="Archive", body="")
        page.output, page.url, page.permalink = output, url, site.url + url
        yield output, render(cfg["templates"]["list"], page=page, list_title="Archive", list_pages=[],
                             list_tag=None, years=site.years, all_tags=None)
