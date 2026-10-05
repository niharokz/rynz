import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from rynz.build import Builder, build
from rynz.errors import BuildError, RynzError
from tests.conftest import FIXTURES, post


def read(root: Path, rel: str) -> str:
    return (root / "public" / rel).read_text(encoding="utf-8")


def test_full_build_writes_pages_feed_sitemap_robots(site):
    root = site(files={
        "content/home.md": "Welcome.",
        "content/note/new.md": post("Newer", date="2026-05-01", description='"The newer one"'),
        "content/note/old.md": post("Older", date="2025-01-01"),
        "content/about.md": post("About", tags="[]"),
    })
    result = build(root)
    assert sorted(result.written)[:3] == ["about.html", "index.html", "new.html"]
    home = read(root, "index.html")
    assert home.index("Newer") < home.index("Older")
    assert "About" not in home.split("<section>")[1]  # pages without the note tag aren't posts

    page = read(root, "new.html")
    assert '<link rel="canonical" href="https://test.example/new.html">' in page
    assert '<meta name="description" content="The newer one">' in page
    assert 'og:image" content=""' not in page
    assert "class=" not in page and "<script" not in page

    feed = ET.fromstring(read(root, "rss.xml"))
    assert feed.findtext("channel/link") == "https://test.example/"
    assert feed.findtext("channel/description")
    assert [i.findtext("title") for i in feed.iter("item")] == ["Newer", "Older"]

    urls = [e.text for e in ET.fromstring(read(root, "sitemap.xml")).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert "https://test.example/about.html" in urls
    assert "Sitemap: https://test.example/sitemap.xml" in read(root, "robots.txt")


def test_prev_next_and_reading_time(site):
    root = site(files={
        "content/a.md": post("A", date="2026-01-01"),
        "content/b.md": post("B", date="2026-02-01"),
        "content/c.md": post("C", date="2026-03-01", body="word " * 450),
    })
    result = build(root)
    b = result.site.page("b")
    assert b.prev.slug == "a" and b.next.slug == "c"
    assert result.site.page("c").reading_time == 3


def test_noindex_nofeed_and_drafts(site):
    root = site(files={
        "content/a.md": post("Visible"),
        "content/b.md": post("Hidden", noindex="true", nofeed="true"),
        "content/c.md": post("Draft", draft="true"),
    })
    build(root)
    assert "Hidden" not in read(root, "rss.xml")
    assert "b.html" not in read(root, "sitemap.xml")
    assert not (root / "public" / "c.html").exists()
    build(root, drafts=True)
    assert (root / "public" / "c.html").exists()


@pytest.mark.parametrize("style, file, link", [
    ("flat", "x.html", 'href="/x.html"'),
    ("clean", "x.html", 'href="/x"'),
    ("pretty", "x/index.html", 'href="/x/"'),
])
def test_url_styles_end_to_end(site, style, file, link):
    root = site({"urls": style}, files={"content/x.md": post("X")})
    build(root)
    assert (root / "public" / file).exists()
    assert link in read(root, "index.html")


def test_tags_archive_redirects_opml_gemini(site):
    root = site(
        {"tags": True, "archive": True, "opml": True, "gemini": True},
        files={
            "content/a.md": post("Alpha", date="2025-03-01", tags="[note, linux]", aliases="[old-alpha]",
                                 body="See [about](/about.html).\n\n- item"),
            "content/b.md": post("Beta", date="2026-03-01", tags="[note, homelab]"),
            "data/blogroll.yml": "- title: Friend\n  url: https://friend.example\n  feed: https://friend.example/rss\n",
        },
    )
    build(root)
    out = root / "public"
    assert "Alpha" in read(root, "tag/linux.html") and "Beta" not in read(root, "tag/linux.html")
    assert "homelab" in read(root, "tag.html")
    assert (out / "tag/linux.xml").exists()
    archive = read(root, "archive.html")
    assert archive.index("2026") < archive.index("2025")
    redirect = read(root, "old-alpha.html")
    assert 'http-equiv="refresh" content="0; url=https://test.example/a.html"' in redirect
    assert 'xmlUrl="https://friend.example/rss"' in read(root, "blogroll.opml")
    gmi = read(root, "gemini/a.gmi")
    assert gmi.startswith("# Alpha") and "=> https://test.example/about.html about" in gmi
    assert "=> a.gmi 2025-03-01 Alpha" in read(root, "gemini/index.gmi")
    assert "https://test.example/tag/linux.html" in read(root, "sitemap.xml")


def test_errors_are_collected_and_fail_the_build(site):
    root = site(files={"content/a.md": "---\ntitle: [broken\n---\n", "content/b.md": post("B")})
    with pytest.raises(RynzError, match="invalid frontmatter"):
        build(root)


def test_template_error_names_the_page(site):
    root = site(files={"content/a.md": post("A", template="broken.html"),
                       "template/broken.html": "{{ page.title | nosuchfilter }}"})
    with pytest.raises((BuildError, RynzError)):
        build(root)


@pytest.mark.parametrize("output", [".", "..", "content", "/tmp"])
def test_output_folder_safety(site, output):
    root = site({"paths": {"output": output}}, files={"content/a.md": post("A")})
    with pytest.raises(RynzError, match="refusing|would delete"):
        build(root)
    assert (root / "config.yml").exists() and (root / "content" / "a.md").exists()


def test_incremental_build_skips_unchanged_pages(site):
    root = site(files={"content/a.md": post("A"), "content/b.md": post("B", date="2025-01-01")})
    build(root)
    second = Builder(root, incremental=True).build()
    assert second.skipped == 2
    (root / "content" / "b.md").write_text(post("B changed", date="2025-01-01"), encoding="utf-8")
    third = Builder(root, incremental=True).build()
    assert "b.html" in third.written
    assert "B changed" in read(root, "b.html")


def test_static_files_override_theme(site):
    root = site(files={"content/a.md": post("A"), "static/nss.css": "/* mine */"})
    build(root)
    assert read(root, "nss.css") == "/* mine */"


def test_project_template_overrides_theme(site):
    root = site(files={"content/a.md": post("A"), "template/note.html": "custom {{ page.title }}"})
    build(root)
    assert read(root, "a.html") == "custom A"


# Compatibility with rynz 1.x ---------------------------------------------------

V1 = FIXTURES / "v1_output"


def test_1x_project_pages_without_new_markdown_are_byte_identical(legacy_site):
    build(legacy_site)
    for name in ("index.html", "older.html"):
        assert read(legacy_site, name) == (V1 / name).read_text(encoding="utf-8"), name


def test_1x_project_gets_the_intended_fixes(legacy_site):
    build(legacy_site)
    resume = read(legacy_site, "resume.html")
    assert "<li>PL/SQL, RDBMS</li>" in resume and "- PL/SQL" in (V1 / "resume.html").read_text()
    code = read(legacy_site, "code_post.html")
    assert "<table>" in code and '<pre style="background:' in code
    rss = read(legacy_site, "rss.xml")
    assert "<description>Write anything that human and machine can understand.</description>" in rss
    assert (legacy_site / "public" / "sitemap.xml").exists()
