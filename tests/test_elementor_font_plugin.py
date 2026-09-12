from pathlib import Path

from morpher.fonts import FontFace, FontRequest, FontResolution, FontSource
from morpher.ir.nodes import DesignNode
from morpher.ir.styles import DesignStyle
from morpher.ir.typography import FontIntent
from morpher.renderers.elementor_font_plugin import render_elementor_font_plugin


def _resolution(face: FontFace, intent: FontIntent) -> FontResolution:
    return FontResolution(
        status="exact",
        request=FontRequest(intent.family, intent.weight, intent.style, intent.flavor),
        face=face,
        provenance="cache_hit",
    )


def _missing_resolution(intent: FontIntent) -> FontResolution:
    return FontResolution(
        status="missing",
        request=FontRequest(intent.family, intent.weight, intent.style, intent.flavor),
        face=None,
        provenance="missing_after_refresh",
    )


def test_morpher_plugin_packages_exact_face_and_enqueues_for_preview(tmp_path: Path) -> None:
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
        children=[DesignNode(kind="text", text="Newsletter", style=DesignStyle(font=intent))],
    )

    def resolver(*args):
        return _resolution(face, args[2])

    plugin = render_elementor_font_plugin(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        output_dir=tmp_path / "morpher-plugin",
        resolver=resolver,
    )

    php = (plugin / "morpher-plugin.php").read_text(encoding="utf-8")
    css = (plugin / "assets" / "fonts.css").read_text(encoding="utf-8")

    assert "Plugin Name: Morpher" in php
    assert "elementor/preview/enqueue_styles" in php
    assert "elementor/editor/after_enqueue_styles" in php
    assert (plugin / "assets" / "fonts" / source.name).exists()
    assert (plugin / "assets" / "fonts.json").exists()
    assert '@font-face {' in css
    assert 'font-family: "HK Grotesk";' in css
    assert "font-weight: 700;" in css
    assert 'url("fonts/HKGrotesk-BoldLegacy.woff2") format("woff2")' in css


def test_morpher_plugin_preserves_faces_from_previous_renders(tmp_path: Path) -> None:
    font_root = tmp_path / "fonts"
    font_root.mkdir()
    bold_source = font_root / "HKGrotesk-BoldLegacy.woff2"
    medium_source = font_root / "HKGrotesk-Medium.woff2"
    bold_source.write_bytes(b"bold")
    medium_source.write_bytes(b"medium")

    bold = FontFace("HK Grotesk", 700, "normal", "legacy", (FontSource(bold_source, "woff2"),))
    medium = FontFace("HK Grotesk", 500, "normal", None, (FontSource(medium_source, "woff2"),))
    plugin_dir = tmp_path / "morpher-plugin"

    bold_intent = FontIntent("HK Grotesk", 700, "normal", "legacy")
    medium_intent = FontIntent("HK Grotesk", 500, "normal", None)

    def resolver(*args):
        intent = args[2]
        face = bold if intent.weight == 700 else medium
        return _resolution(face, intent)

    render_elementor_font_plugin(
        DesignNode(kind="container", children=[DesignNode(kind="text", style=DesignStyle(font=bold_intent))]),
        font_root=font_root,
        font_cache=font_root / "font-registry.json",
        output_dir=plugin_dir,
        resolver=resolver,
    )
    render_elementor_font_plugin(
        DesignNode(kind="container", children=[DesignNode(kind="text", style=DesignStyle(font=medium_intent))]),
        font_root=font_root,
        font_cache=font_root / "font-registry.json",
        output_dir=plugin_dir,
        resolver=resolver,
    )

    css = (plugin_dir / "assets" / "fonts.css").read_text(encoding="utf-8")
    assert css.count("@font-face") == 2
    assert "font-weight: 700;" in css
    assert "font-weight: 500;" in css
    assert (plugin_dir / "assets" / "fonts" / bold_source.name).exists()
    assert (plugin_dir / "assets" / "fonts" / medium_source.name).exists()


def test_morpher_plugin_deduplicates_same_resolved_face(tmp_path: Path) -> None:
    source = tmp_path / "fonts" / "HKGrotesk-BoldLegacy.woff2"
    source.parent.mkdir()
    source.write_bytes(b"font")
    face = FontFace("HK Grotesk", 700, "normal", "legacy", (FontSource(source, "woff2"),))
    intent = FontIntent("HK Grotesk", 700, "normal", "legacy")
    root = DesignNode(
        kind="container",
        children=[
            DesignNode(kind="text", text="A", style=DesignStyle(font=intent)),
            DesignNode(kind="text", text="B", style=DesignStyle(font=intent)),
        ],
    )

    def resolver(*args):
        return _resolution(face, args[2])

    plugin = render_elementor_font_plugin(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        output_dir=tmp_path / "plugin",
        resolver=resolver,
    )

    css = (plugin / "assets" / "fonts.css").read_text(encoding="utf-8")
    assert css.count("@font-face") == 1


def test_morpher_plugin_emits_deduplicated_missing_font_diagnostic(tmp_path: Path) -> None:
    intent = FontIntent("Big Caslon", 500, "normal", None)
    root = DesignNode(
        kind="container",
        children=[
            DesignNode(kind="text", text="A", style=DesignStyle(font=intent)),
            DesignNode(kind="text", text="B", style=DesignStyle(font=intent)),
        ],
    )

    def resolver(*args):
        return _missing_resolution(args[2])

    plugin = render_elementor_font_plugin(
        root,
        font_root=tmp_path / "fonts",
        font_cache=tmp_path / "fonts" / "font-registry.json",
        output_dir=tmp_path / "plugin",
        resolver=resolver,
    )

    css = (plugin / "assets" / "fonts.css").read_text(encoding="utf-8")
    assert css.count('/* MORPHER FONT: "Big Caslon" is unavailable */') == 1
