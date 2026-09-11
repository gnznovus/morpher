from pathlib import Path

from morpher.fonts import FontFace, FontRequest, FontResolution, FontSource
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.ir.typography import FontIntent
from morpher.renderers.elementor_font_plugin import render_elementor_font_plugin


def test_elementor_font_plugin_packages_exact_face_and_enqueues_for_preview(tmp_path: Path) -> None:
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

    root = DesignNode(
        kind="container",
        children=[
            DesignNode(
                kind="text",
                text="Newsletter",
                style=DesignStyle(font=FontIntent("HK Grotesk", 700, "normal", "legacy")),
            )
        ],
    )

    def resolver(*args):
        intent = args[2]
        return FontResolution(
            status="exact",
            request=FontRequest(intent.family, intent.weight, intent.style, intent.flavor),
            face=face,
            provenance="cache_hit",
        )

    plugin = render_elementor_font_plugin(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        output_dir=tmp_path / "morpher-font-injector",
        resolver=resolver,
    )

    php = (plugin / "morpher-font-injector.php").read_text(encoding="utf-8")
    css = (plugin / "assets" / "fonts.css").read_text(encoding="utf-8")

    assert "Plugin Name: Morpher Font Injector" in php
    assert "elementor/preview/enqueue_styles" in php
    assert "elementor/editor/after_enqueue_styles" in php
    assert (plugin / "assets" / "fonts" / source.name).exists()
    assert '@font-face {' in css
    assert 'font-family: "HK Grotesk";' in css
    assert "font-weight: 700;" in css
    assert 'url("fonts/HKGrotesk-BoldLegacy.woff2") format("woff2")' in css


def test_elementor_font_plugin_deduplicates_same_resolved_face(tmp_path: Path) -> None:
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

    intent = FontIntent("HK Grotesk", 700, "normal", "legacy")
    root = DesignNode(
        kind="container",
        children=[
            DesignNode(kind="text", text="A", style=DesignStyle(font=intent)),
            DesignNode(kind="text", text="B", style=DesignStyle(font=intent)),
        ],
    )

    def resolver(*args):
        return FontResolution(
            status="exact",
            request=FontRequest("HK Grotesk", 700, "normal", "legacy"),
            face=face,
            provenance="cache_hit",
        )

    plugin = render_elementor_font_plugin(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        output_dir=tmp_path / "plugin",
        resolver=resolver,
    )

    css = (plugin / "assets" / "fonts.css").read_text(encoding="utf-8")
    assert css.count("@font-face") == 1
