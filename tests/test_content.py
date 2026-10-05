import datetime as dt

import pytest

from rynz import config
from rynz.content import assign_urls, discover, output_for, slugify, split_frontmatter
from rynz.errors import ContentError
from tests.conftest import post


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Café  déjà vu") == "cafe-deja-vu"
    assert slugify("!!!") == "untitled"


@pytest.mark.parametrize("style, expected", [
    ("flat", ("about.html", "/about.html")),
    ("clean", ("about.html", "/about")),
    ("pretty", ("about/index.html", "/about/")),
])
def test_url_styles(style, expected):
    assert output_for("about", style) == expected


def test_frontmatter_error_points_at_line(tmp_path):
    path = tmp_path / "x.md"
    with pytest.raises(ContentError) as err:
        split_frontmatter("---\ntitle: ok\ndate: [bad\n---\nbody", path)
    assert err.value.line and err.value.line >= 2


def test_unclosed_frontmatter(tmp_path):
    with pytest.raises(ContentError, match="never closes"):
        split_frontmatter("---\ntitle: x\n", tmp_path / "x.md")


def test_pages_at_any_depth_and_drafts(site):
    root = site(files={
        "content/note/a.md": post("A"),
        "content/note/2026/deep.md": post("Deep"),
        "content/note/wip.md": post("WIP", draft="true"),
        "content/_hidden/skip.md": post("Hidden"),
        "content/home.md": "Home text",
    })
    cfg = config.load(root)
    slugs = sorted(p.slug for p in discover(cfg))
    assert slugs == ["a", "deep"]
    assert "wip" in [p.slug for p in discover(cfg, include_drafts=True)]


def test_page_fields(site):
    root = site(files={"content/x.md": post(
        "X", date="2026-02-03", updated="2026-03-04", tags="[note, linux]",
        slug="custom", description='"About X"', aliases="[old-x]", noindex="true", colour="blue")})
    page = discover(config.load(root))[0]
    assert page.slug == "custom"
    assert page.date == dt.date(2026, 2, 3)
    assert page.last_updated == dt.date(2026, 3, 4)
    assert page.tags == ["note", "linux"]
    assert page.description == "About X"
    assert page.aliases == ["old-x"]
    assert page.noindex is True
    assert page.extra == {"colour": "blue"}


def test_duplicate_slug_is_an_error(site):
    root = site(files={"content/a/x.md": post("One"), "content/b/x.md": post("Two")})
    cfg = config.load(root)
    with pytest.raises(ContentError, match="duplicate slug `x`"):
        assign_urls(discover(cfg), cfg)


def test_bad_date_is_explained(site):
    root = site(files={"content/x.md": post("X", date="'next week'")})
    with pytest.raises(ContentError, match="must be a date"):
        discover(config.load(root))


def test_page_works_like_a_1x_dict(site):
    root = site(files={"content/x.md": post("X", subtitle='"sub"')})
    cfg = config.load(root)
    page = discover(cfg)[0]
    assign_urls([page], cfg)
    assert page["url"] == "/x.html"
    assert page["subtitle"] == "sub"
    assert page.get("missing", "default") == "default"
