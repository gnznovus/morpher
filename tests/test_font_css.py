from pathlib import Path

from morpher.fonts import (
    FontFace,
    FontRequest,
    FontResolution,
    FontSource,
    package_font_face,
    render_font_resolution_css,
)


def _face(tmp_path: Path) -> FontFace:
    woff2 = tmp_path / "HKGrotesk-BoldLegacy.woff2"
    woff = tmp_path / "HKGrotesk-BoldLegacy.woff"
    woff.write_bytes(b"woff")
    woff2.write_bytes(b"woff2")
    return FontFace(
        family="HK Grotesk",
        weight=700,
        style="normal",
        flavor="legacy",
        sources=(FontSource(woff, "woff"), FontSource(woff2, "woff2")),
    )


def test_packages_all_sources_for_resolved_face(tmp_path: Path) -> None:
    face = _face(tmp_path)
    destination = tmp_path / "output" / "fonts"

    packaged = package_font_face(face, destination)

    assert {path.name for path in packaged.values()} == {
        "HKGrotesk-BoldLegacy.woff2",
        "HKGrotesk-BoldLegacy.woff",
    }
    assert all(path.exists() for path in packaged.values())


def test_renders_web_sources_in_preferred_order_without_success_diagnostic(tmp_path: Path) -> None:
    face = _face(tmp_path)
    destination = tmp_path / "native" / "assets" / "fonts"
    packaged = package_font_face(face, destination)
    resolution = FontResolution(
        status="exact",
        request=FontRequest("HK Grotesk", 700, "normal", "legacy"),
        face=face,
        provenance="cache_hit",
    )

    css = render_font_resolution_css(
        resolution,
        packaged_sources=packaged,
        css_dir=tmp_path / "native",
    )

    assert "@font-face {" in css
    assert 'font-family: "HK Grotesk";' in css
    assert "font-weight: 700;" in css
    assert "font-style: normal;" in css
    assert css.index("HKGrotesk-BoldLegacy.woff2") < css.index("HKGrotesk-BoldLegacy.woff\"")
    assert 'url("assets/fonts/HKGrotesk-BoldLegacy.woff2") format("woff2")' in css
    assert "MORPHER FONT" not in css
    assert "registry cache hit" not in css


def test_renders_fallback_without_diagnostic(tmp_path: Path) -> None:
    face = _face(tmp_path)
    resolution = FontResolution(
        status="fallback",
        request=FontRequest("HK Grotesk", 600, "normal"),
        face=face,
        reason="requested face unavailable",
        provenance="fallback_after_refresh",
    )

    css = render_font_resolution_css(resolution)

    assert "@font-face {" in css
    assert "MORPHER FONT" not in css
    assert "fallback after registry refresh" not in css


def test_renders_simple_missing_font_warning() -> None:
    resolution = FontResolution(
        status="missing",
        request=FontRequest("Not Existed Font", 700, "normal"),
        provenance="missing_after_refresh",
    )

    css = render_font_resolution_css(resolution)

    assert css == '/* MORPHER FONT: "Not Existed Font" is unavailable */\n'
    assert "@font-face" not in css
