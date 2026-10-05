"""`rynz check`: look over the built site for problems a reader would hit."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


@dataclass
class Issue:
    level: str  # "error" or "warning"
    file: str
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    files: int = 0

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.images_without_alt: list[str] = []
        self.title = ""
        self.has_description = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if a.get("name") and tag == "a":
            self.ids.add(a["name"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag in ("img", "script", "source") and a.get("src"):
            self.links.append(a["src"])
            if tag == "img" and not (a.get("alt") or "").strip():
                self.images_without_alt.append(a["src"])
        elif tag == "link" and a.get("href") and a.get("rel") in ("stylesheet", "icon", "shortcut icon"):
            self.links.append(a["href"])
        elif tag == "meta" and a.get("name") == "description" and (a.get("content") or "").strip():
            self.has_description = True
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _resolve(out: Path, current: Path, href: str) -> Path | None:
    """The file a link points to, trying the forms static hosts serve (x, x.html, x/index.html)."""
    path = unquote(urlparse(href).path)
    base = out / path.lstrip("/") if path.startswith("/") else current.parent / path
    candidates = [base]
    if path.endswith("/") or path == "":
        candidates = [base / "index.html"]
    else:
        candidates += [base.with_name(base.name + ".html"), base / "index.html"]
    return next((c for c in candidates if c.is_file()), None)


def check_site(out: Path, site_url: str = "") -> Report:
    report = Report()
    pages: dict[Path, _Page] = {}
    for path in sorted(out.rglob("*.html")):
        parser = _Page()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        pages[path.resolve()] = parser
    report.files = len(pages)
    host = urlparse(site_url).netloc

    for path, page in pages.items():
        rel = str(path.relative_to(out.resolve()))
        is_redirect = 'http-equiv="refresh"' in path.read_text(encoding="utf-8", errors="replace")
        if not page.title.strip():
            report.issues.append(Issue("error", rel, "page has no <title>"))
        if not page.has_description and not is_redirect:
            report.issues.append(Issue("warning", rel, "no meta description"))
        for src in page.images_without_alt:
            report.issues.append(Issue("warning", rel, f"image without alt text: {src}"))
        for href in page.links:
            parsed = urlparse(href)
            if parsed.scheme in ("mailto", "tel", "data", "javascript") or href.startswith("//"):
                continue
            if parsed.scheme in ("http", "https"):
                if not host or parsed.netloc != host:
                    continue  # external links are not checked (no network calls)
                href = parsed.path + (f"#{parsed.fragment}" if parsed.fragment else "")
                parsed = urlparse(href)
            if not parsed.path and parsed.fragment:
                if parsed.fragment not in page.ids:
                    report.issues.append(Issue("error", rel, f"anchor #{parsed.fragment} not found on this page"))
                continue
            target = _resolve(out.resolve(), path, href)
            if target is None:
                report.issues.append(Issue("error", rel, f"broken link: {href}"))
            elif parsed.fragment and target.resolve() in pages and parsed.fragment not in pages[target.resolve()].ids:
                report.issues.append(Issue("error", rel, f"anchor #{parsed.fragment} not found in {href}"))
    return report
