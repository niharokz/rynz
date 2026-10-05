"""An OPML blogroll from a data file, e.g. data/blogroll.yml:

    - title: Example blog
      url: https://example.com
      feed: https://example.com/feed.xml
"""

from __future__ import annotations

from rynz.errors import ContentError


def register(rynz):
    @rynz.generator
    def opml(site, render):
        opts = site.config["opml"]
        if not opts.get("enabled"):
            return
        name = opts.get("data", "blogroll")
        entries = site.data.get(name)
        if not isinstance(entries, list):
            raise ContentError(f"opml is on, but data/{name}.yml is missing or not a list")
        yield opts.get("output", "blogroll.opml"), render("opml.xml", entries=entries)
