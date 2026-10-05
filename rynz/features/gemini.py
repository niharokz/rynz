"""A Gemini capsule (gemtext) built from the same Markdown.

Off by default. Turn it on with `gemini: true` and serve the output's
`gemini/` folder with any Gemini server.
"""

from __future__ import annotations

import re

_LINK = re.compile(r"!?\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def register(rynz):
    @rynz.generator
    def gemini(site, render):
        cfg = site.config
        opts = cfg["gemini"]
        if not opts.get("enabled"):
            return
        base = opts.get("output", "gemini").strip("/")
        for page in site.pages:
            yield f"{base}/{page.slug}.gmi", page_to_gemtext(page, cfg["url"])
        lines = [f"# {cfg['title']}", ""]
        if cfg.get("description"):
            lines += [cfg["description"], ""]
        lines.append("## Posts")
        for post in site.posts:
            date = post.date.isoformat() + " " if post.date else ""
            lines.append(f"=> {post.slug}.gmi {date}{post.title}")
        yield f"{base}/index.gmi", "\n".join(lines) + "\n"


def page_to_gemtext(page, site_url: str) -> str:
    out = [f"# {page.title}", ""]
    if page.description:
        out += [page.description, ""]
    out += markdown_to_gemtext(page.body, site_url)
    if page.last_updated:
        out += ["", f"Last updated {page.last_updated.isoformat()}"]
    return "\n".join(out).rstrip() + "\n"


def markdown_to_gemtext(text: str, site_url: str = "") -> list[str]:
    """A small, honest converter: headings, lists, quotes, code, links on their own lines."""
    out: list[str] = []
    in_code = False
    para: list[str] = []

    def flush() -> None:
        if not para:
            return
        joined = " ".join(s.strip() for s in para)
        links = _LINK.findall(joined)
        out.append(_LINK.sub(lambda m: m.group(1), joined))
        for label, href in links:
            if href.startswith("/"):
                href = site_url + href
            out.append(f"=> {href} {label or href}")
        out.append("")
        para.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            flush()
            out.append("```")
            in_code = not in_code
            continue
        if in_code:
            out.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if heading:
            flush()
            out += ["#" * min(len(heading.group(1)), 3) + " " + heading.group(2), ""]
        elif re.match(r"^([-*+]|\d+\.)\s+", stripped):
            flush()
            item = re.sub(r"^([-*+]|\d+\.)\s+", "", stripped)
            links = _LINK.findall(item)
            out.append("* " + _LINK.sub(lambda m: m.group(1), item))
            for label, href in links:
                out.append(f"=> {site_url + href if href.startswith('/') else href} {label or href}")
        elif stripped.startswith(">"):
            flush()
            out.append("> " + stripped.lstrip("> "))
        elif stripped.startswith("|"):
            flush()
            out.append(stripped)
        else:
            para.append(stripped)
    flush()
    return out
