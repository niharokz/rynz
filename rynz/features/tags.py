"""A page per tag, plus a page listing every tag."""

from __future__ import annotations

from rynz.content import Page, output_for, slugify


def register(rynz):
    @rynz.hook("site")
    def note_tag_urls(site):
        if site.config["tags"].get("enabled"):
            for tag in site.tags:
                site.config.setdefault("_extra_sitemap", []).append(
                    {"loc": site.url + site.tag_url(tag), "lastmod": None})

    @rynz.generator
    def tags(site, render):
        cfg = site.config
        if not cfg["tags"].get("enabled"):
            return
        base = cfg["tags"]["path"]
        for tag, pages in site.tags.items():
            output, url = output_for(f"{base}/{slugify(tag)}", cfg["urls"])
            page = _virtual(site, f"Tagged: {tag}", output, url)
            yield output, render(cfg["templates"]["list"], page=page, list_title=f"Tagged: {tag}",
                                 list_pages=pages, list_tag=tag, years=None, all_tags=None)
        output, url = output_for(base, cfg["urls"])
        page = _virtual(site, "Tags", output, url)
        yield output, render(cfg["templates"]["list"], page=page, list_title="Tags", list_pages=[],
                             list_tag=None, years=None, all_tags=site.tags)


def _virtual(site, title, output, url):
    page = Page(source=site.config["_root"], slug=output, title=title, body="")
    page.output, page.url, page.permalink = output, url, site.url + url
    return page
