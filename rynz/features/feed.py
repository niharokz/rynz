"""RSS 2.0 feed for posts, plus one feed per tag when tag pages are on."""

from __future__ import annotations

from rynz.content import slugify


def register(rynz):
    @rynz.generator
    def feed(site, render):
        cfg = site.config
        opts = cfg["feed"]
        if not opts.get("enabled"):
            return
        posts = [p for p in site.posts if not p.nofeed]
        if opts.get("limit"):
            posts = posts[: opts["limit"]]
        output = opts.get("output", "rss.xml")
        yield output, _render(site, render, opts["template"], posts, output, cfg["title"], cfg["description"])

        if opts.get("tag_feeds") and cfg["tags"].get("enabled"):
            for tag, pages in site.tags.items():
                tagged = [p for p in pages if not p.nofeed]
                path = f"{cfg['tags']['path']}/{slugify(tag)}.xml"
                yield path, _render(site, render, "feed.xml", tagged, path,
                                    f"{cfg['title']} · {tag}", f"Posts tagged {tag}")


def _render(site, render, template, posts, output, title, description):
    cfg = site.config
    feed_url = f"{cfg['url']}/{output}"
    last = next((p.last_updated for p in posts if p.last_updated), None)
    return render(
        template,
        feed_posts=posts,
        feed_url=feed_url,
        feed_title=title,
        feed_description=description,
        feed_updated=last or site.built,
        full_content=cfg["feed"].get("full_content", False),
        # rynz 1.x feed template names
        title=cfg["title"],
        url=feed_url,
        posts=list(site.pages),
        last_date=last or site.built,
        subtitle=cfg["description"],
    )
