import pytest

from rynz import config
from rynz.errors import ConfigError


def test_minimal_config_gets_defaults(site):
    root = site()
    cfg = config.load(root)
    assert cfg["title"] == "Test site"
    assert cfg.paths.output == "public"
    assert cfg["feed"]["enabled"] is True
    assert cfg["urls"] == "flat"


def test_url_trailing_slash_is_removed(site):
    cfg = config.load(site({"url": "https://test.example/"}))
    assert cfg["url"] == "https://test.example"


@pytest.mark.parametrize("bad, message", [
    ({"title": ""}, "`title` is required"),
    ({"url": "test.example"}, "must start with http"),
    ({"urls": "fancy"}, "`urls` must be one of"),
    ({"menu": [{"name": "x"}]}, "`menu` must be a list"),
])
def test_invalid_config_is_explained(site, bad, message):
    with pytest.raises(ConfigError, match=message):
        config.load(site(bad))


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError, match="config.yml not found"):
        config.load(tmp_path)


def test_yaml_error_has_line_number(tmp_path):
    (tmp_path / "config.yml").write_text("title: x\nurl: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError) as err:
        config.load(tmp_path)
    assert err.value.line is not None


def test_legacy_keys_are_mapped_and_kept(legacy_site):
    cfg = config.load(legacy_site, warn_legacy=False)
    assert cfg.paths.output == "public"
    assert cfg["templates"]["note"] == "template/note_template.html"
    assert cfg["description"].startswith("Write anything")
    assert cfg["desc"] == cfg["description"]  # old templates can still read config.get('desc')
    assert cfg["templates"]["trim_blocks"] is False


def test_section_shorthand(site):
    cfg = config.load(site({"tags": True, "feed": False}))
    assert cfg["tags"]["enabled"] is True and cfg["tags"]["path"] == "tag"
    assert cfg["feed"]["enabled"] is False
