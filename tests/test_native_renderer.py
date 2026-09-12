from pathlib import Path

from morpher.fonts import FontFace, FontRequest, FontResolution, FontSource
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.ir.typography import FontIntent
from morpher.renderers.native_css import render_native_css
from morpher.renderers.native_html import render_native_html


def _text() -> DesignNode:
    return DesignNode(
        kind="text",
        name="Newsletter Title",
        source_id="45:5221",
        text="STAY TUNE - SUBSCRIBE TO OUR NEWSLETTER",
        style=DesignStyle(
            font=FontIntent("HK Grotesk", 700, "normal", "legacy"),
            font_size=30,
            line_height=36.005859375,
            letter_spacing=3,
            text_color="#FF6B00",
            text_align_horizontal="LEFT",
        ),
    )


def test_native_html_keeps_real_text_and_stable_identity() -> None:
    html = render_native_html(_text())

    assert "STAY TUNE - SUBSCRIBE TO OUR NEWSLETTER" in html
    assert 'id="morpher-45-5221"' in html
    assert 'class="morpher-45-5221"' in html
    assert 'data-morpher-source-id="45:5221"' in html
    assert "morpher-text-outline" not in html
    assert "<img" not in html


def test_native_css_uses_resolved_face_and_packages_font(tmp_path: Path) -> None:
    source = tmp_path / "fonts" / "HKGrotesk-BoldLegacy.woff2"
    source.parent.mkdir()
    source.write_bytes(b"font")
    face = FontFace(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
        sources=(FontSource(source, "woff2"),),
    )

    def resolver(*args):
        intent = args[2]
        return FontResolution(
            status="exact",
            request=FontRequest(intent.family, intent.weight, intent.style, intent.flavor),
            face=face,
            provenance="cache_hit",
        )

    native = tmp_path / "native"
    css = render_native_css(
        _text(),
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        font_asset_dir=native / "assets" / "fonts",
        css_dir=native,
        resolver=resolver,
    )

    assert (native / "assets" / "fonts" / source.name).exists()
    assert '@font-face {' in css
    assert 'url("assets/fonts/HKGrotesk-BoldLegacy.woff2") format("woff2")' in css
    assert '.morpher-45-5221 {' in css
    assert 'font-family: "HK Grotesk";' in css
    assert "font-size: 30px;" in css
    assert "line-height: 36.0059px;" in css
    assert "letter-spacing: 3px;" in css
    assert "text-align: left;" in css


def test_native_css_warns_only_when_font_is_unavailable(tmp_path: Path) -> None:
    def resolver(*args):
        intent = args[2]
        return FontResolution(
            status="missing",
            request=FontRequest(intent.family, intent.weight, intent.style, intent.flavor),
            provenance="missing_after_refresh",
        )

    css = render_native_css(
        _text(),
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        font_asset_dir=tmp_path / "native" / "assets" / "fonts",
        css_dir=tmp_path / "native",
        resolver=resolver,
    )

    assert '/* MORPHER FONT: "HK Grotesk" is unavailable */' in css
    assert "registry cache hit" not in css
    assert "MORPHER WARNING" not in css
