from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMMON_CSS = PROJECT_ROOT / "frontend" / "assets" / "css" / "common.css"
COMMON_JS = PROJECT_ROOT / "frontend" / "assets" / "js" / "common.js"


def test_common_css_does_not_globally_hide_sidebar_or_aside():
    css = COMMON_CSS.read_text(encoding="utf-8")
    assert ".sidebar," not in css
    assert "aside" not in css


def test_common_js_does_not_strip_sidebar_or_aside():
    js = COMMON_JS.read_text(encoding="utf-8")
    assert "'.sidebar'" not in js
    assert "'aside'" not in js


def test_common_js_has_keyboard_support_for_nav_dropdown():
    js = COMMON_JS.read_text(encoding="utf-8")
    assert "aria-expanded" in js
    assert "keydown" in js
    assert "Escape" in js
