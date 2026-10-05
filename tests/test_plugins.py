import pytest

from rynz.build import build
from rynz.errors import BuildError, ConfigError
from tests.conftest import post

PLUGIN = '''
def register(rynz):
    @rynz.hook("page")
    def add_flag(page, site):
        page.extra["seen"] = True

    @rynz.hook("html")
    def mark(html, page, site):
        return html.replace("TODO", "<mark>TODO</mark>")

    @rynz.hook("context")
    def ctx(context, page, site):
        context["greeting"] = "hi"

    @rynz.generator
    def humans(site, render):
        yield "humans.txt", "pages: %d" % len(site.pages)

    @rynz.filter("shout")
    def shout(text):
        return text.upper()

    @rynz.hook("done")
    def done(site, written):
        site.config["_done"] = len(written)
'''


def test_user_plugin_file_uses_every_hook(site):
    root = site({"plugins": ["plugins/mine.py"]}, files={
        "plugins/mine.py": PLUGIN,
        "content/a.md": post("A", body="TODO later"),
        "template/note.html": "{{ greeting }} {{ page.title | shout }} {{ page.extra.seen }} {{ page.html }}",
    })
    result = build(root)
    out = (root / "public" / "a.html").read_text()
    assert out.startswith("hi A True")
    assert "<mark>TODO</mark>" in out
    assert (root / "public" / "humans.txt").read_text() == "pages: 1"
    assert result.site.config["_done"] > 0


def test_unknown_hook_is_rejected(site):
    root = site({"plugins": ["plugins/bad.py"]}, files={
        "plugins/bad.py": "def register(rynz):\n    rynz.hook('nope')(lambda: None)\n",
        "content/a.md": post("A"),
    })
    with pytest.raises(ConfigError, match="unknown hook `nope`"):
        build(root)


def test_plugin_cannot_write_outside_output(site):
    root = site({"plugins": ["plugins/evil.py"]}, files={
        "plugins/evil.py": "def register(rynz):\n    @rynz.generator\n    def g(site, render):\n        yield '../escape.txt', 'x'\n",
        "content/a.md": post("A"),
    })
    with pytest.raises(BuildError) as err:
        build(root)
    assert "outside the output folder" in str(err.value.errors[0])
    assert not (root / "escape.txt").exists()


def test_missing_plugin(site):
    root = site({"plugins": ["no_such_plugin_module"]}, files={"content/a.md": post("A")})
    with pytest.raises(ConfigError, match="cannot import plugin"):
        build(root)
