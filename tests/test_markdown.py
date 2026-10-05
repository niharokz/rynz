import struct
import zlib

from rynz import config
from rynz.markdown import Renderer, image_size, word_count


def _renderer(site, **markdown):
    cfg = config.load(site({"markdown": markdown} if markdown else None))
    return Renderer(cfg), cfg


def test_extras_are_on(site):
    md, _ = _renderer(site)
    html, _ = md.render("| a | b |\n|---|---|\n| 1 | 2 |\n\n**Label**\n- one\n- two\n\n~~old~~\n")
    assert "<table>" in html
    assert "<li>one</li>" in html
    assert "<s>old</s>" in html


def test_highlighting_uses_inline_styles_not_classes(site):
    md, _ = _renderer(site)
    html, _ = md.render("```python\ndef f():\n    return 1\n```\n")
    assert 'style="color:' in html
    assert "class=" not in html
    assert html.startswith('<pre style="background:')


def test_highlighting_can_be_turned_off(site):
    md, _ = _renderer(site, highlight={"enabled": False})
    html, _ = md.render("```python\nx = 1 < 2\n```\n")
    assert html.strip() == "<pre><code>x = 1 &lt; 2</code></pre>"


def test_unknown_language_is_left_plain(site):
    md, _ = _renderer(site)
    html, _ = md.render("```notalanguage\nhello\n```\n")
    assert "<pre><code>hello</code></pre>" in html


def test_classes_stripped_from_footnotes(site):
    md, _ = _renderer(site)
    html, _ = md.render("Text[^1].\n\n[^1]: Note.\n")
    assert "class=" not in html and 'id="fn-1"' in html


def test_classes_kept_when_asked(site):
    md, _ = _renderer(site, strip_classes=False)
    html, _ = md.render("Text[^1].\n\n[^1]: Note.\n")
    assert 'class="footnotes"' in html


def _png(w, h):
    raw = b"\x00" + b"\x00\x00\x00" * w
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw * h)) + chunk(b"IEND", b"")


def test_images_get_lazy_loading_and_size(site, tmp_path):
    root = site(files={"static/img/pic.png": _png(40, 30)})
    md = Renderer(config.load(root))
    html, _ = md.render("![A picture](/img/pic.png)\n\n![remote](https://x.example/a.png)")
    assert 'alt="A picture" loading="lazy" width="40" height="30"' in html
    assert '<img src="https://x.example/a.png" alt="remote" loading="lazy">' in html


def test_image_size_formats(tmp_path):
    png = tmp_path / "a.png"
    png.write_bytes(_png(7, 5))
    gif = tmp_path / "a.gif"
    gif.write_bytes(b"GIF89a" + struct.pack("<HH", 9, 4) + b"\x00" * 20)
    assert image_size(png) == (7, 5)
    assert image_size(gif) == (9, 4)
    assert image_size(tmp_path / "missing.png") is None


def test_word_count_ignores_code():
    assert word_count("one two three\n\n```\nnot counted here\n```\n") == 3
